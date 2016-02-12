# coding utf-8
"""Test the functionality in RPM repos when `remove_missing`_ is set to True.

Following steps are executed in order to test correct functionality
of repository created with valid feed and remove_missing option set.

1. Create repository foo with valid feed, run sync, add distributor to it
   and publish over http and https (RemoveMissingTestCase).
2. Create second repository, bar, with feed pointing to first repository and
   set remove_missing=True (RemoveMissingTrueTestCase) and remove_missing=False
   respectively (RemoveMissingFalseTestCase) and run sync on them.
3. Assert that repositories contain same set of units.
4. Remove random unit from repository foo and publish.
5. Sync bar repo (RemoveMissingFalseTestCase, RemoveMissingFalseTestCase).
6. Assert that:
    * when rm_missing=True, content of foo and bar is same
    * when rm_missing=False, content of foo and bar differ

.. _remove missing:
    https://pulp-rpm.readthedocs.org/en/latest/tech-reference/yum-plugins.html
"""

from __future__ import unicode_literals

import random
import unittest2

try:  # try Python 3 import first
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse  # pylint:disable=C0411,E0401


from pulp_smash import api, config, utils
from pulp_smash.constants import (
    REPOSITORY_PATH,
    RPM_FEED_URL,
)

_PUBLISH_DIR = 'pulp/repos/'


def _gen_repo():
    """Return a semi-random dict for use in creating an RPM repostirory."""
    return {
        'id': utils.uuid4(),
        'importer_config': {},
        'importer_type_id': 'yum_importer',
        'notes': {'_repo-type': 'rpm-repo'},
    }


def _gen_distributor():
    """Return a semi-random dict for use in creating a YUM distributor."""
    return {
        'auto_publish': False,
        'distributor_id': utils.uuid4(),
        'distributor_type_id': 'yum_distributor',
        'distributor_config': {
            'http': True,
            'https': True,
            'relative_url': utils.uuid4() + '/',
        },
    }


class _CommonTestsMixin(object):
    """Common tests for RemoveMissing* classes."""

    def test_status_code(self):
        """Verify th HTTP status code of each server response."""
        for step, code in (
                ('sync', 202),
                ('publish', 202),
                ('units before removal', 200),
                ('units after removal', 200),
        ):
            with self.subTest(step=step):
                for response in self.responses[step]:
                    self.assertEqual(response.status_code, code)
        for step, code in (
                ('distribute', 201),
                ('remove unit', 202),
        ):
            with self.subTest(step=step):
                self.assertEqual(self.responses[step].status_code, code)

    def test_units_before_removal(self):
        """Test that units in repositories before removal are the same."""
        bodies = [re.json() for re in self.responses['units before removal']]
        # Package category and package group will differ so we count only RPMs
        self.assertEqual(
            set(unit['unit_id'] for unit in bodies[0]
                if unit['unit_type_id'] == 'rpm'),  # This test is fragile
            set(unit['unit_id'] for unit in bodies[1]
                if unit['unit_type_id'] == 'rpm'),  # due to hard-coded
        )  # indices. But the data is complex, and this makes things simpler.

    def test_unit_removed(self):
        """Test that correct unit from first repository has been removed."""
        body = self.responses['units after removal'][0].json()
        units_names = set(unit['metadata']['name'] for unit in body
                          if unit['unit_type_id'] == 'rpm')
        self.assertNotIn(self.removed_unit, units_names)


class _BaseTestCase(unittest2.TestCase):
    """Parent class for RemoveMissingTrueTestCase and RemoveMissingFalseTestCase.

    Provides server config, tear down created resources and common
    functionality shared by child classes.
    """

    @classmethod
    def setUpClass(cls, rm_missing=False):  # pylint:disable=arguments-differ
        """Create two repositories, first is feed of second one.

        Provides server config and set of iterable to delete.
        Following steps are executed:
            1. Create repository foo with feed, sync and publish it.
            2. Create repository bar with foo as a feed and run sync.
            3. Get content of both repositories.
            4. Remove random unit from repository foo and publish foo.
            5. Sync repository bar.
            6. Get content of both repositories.
        """
        cls.cfg = config.get_config()
        cls.resources = set()

        cls.responses = {}
        client = api.Client(cls.cfg, api.safe_handler)

        bodies = tuple((_gen_repo() for _ in range(2)))
        bodies[0]['importer_config']['feed'] = RPM_FEED_URL
        repos = []
        repos.append(client.post(REPOSITORY_PATH, bodies[0]).json())
        sync_path = urljoin(repos[0]['_href'], 'actions/sync/')
        # Run sync and wait for the task to complete
        cls.responses['sync'] = []
        cls.responses['sync'].append(client.post(
            sync_path, {'override_config': {}}
        ))
        # Add distributor and publish
        cls.responses['distribute'] = client.post(
            urljoin(repos[0]['_href'], 'distributors/'),
            _gen_distributor(),
        )
        cls.responses['publish'] = []
        cls.responses['publish'].append(client.post(
            urljoin(repos[0]['_href'], 'actions/publish/'),
            {'id': cls.responses['distribute'].json()['id']},
        ))

        # Use http feed instead of https to avoid possible config problems
        bodies[1]['importer_config']['feed'] = urljoin(
            # Create http url from base_url
            urlparse(cls.cfg.base_url)._replace(scheme='http').geturl(),
            _PUBLISH_DIR +
            cls.responses['distribute'].json()['config']['relative_url'],
        )
        bodies[1]['importer_config']['remove_missing'] = rm_missing
        # Create and sync second repo
        repos.append(client.post(REPOSITORY_PATH, bodies[1]).json())
        sync_path = urljoin(repos[1]['_href'], 'actions/sync/')
        cls.responses['sync'].append(client.post(
            sync_path, {'override_config': {}}
        ))
        # Get content of both repositories
        body = {'criteria': {}}
        cls.responses['units before removal'] = [
            client.post(urljoin(repo['_href'], 'search/units/'), body)
            for repo in repos
        ]
        # Get random unit from first repository to remove
        rpms = [unit['metadata']['name']
                for unit in cls.responses['units before removal'][0].json()
                if unit['unit_type_id'] == 'rpm']
        cls.removed_unit = random.choice(rpms)
        # Remove unit from first repo and publish again
        cls.responses['remove unit'] = client.post(
            urljoin(repos[0]['_href'], 'actions/unassociate/'),
            {'criteria':
                {'fields':
                    {'unit': ['name', 'epoch', 'version', 'release',
                              'arch', 'checksum', 'checksumtype']},
                    'type_ids': ['rpm'],
                    'filters': {'unit': {'name': cls.removed_unit}}}},)
        # Publish first repo again
        cls.responses['publish'].append(client.post(
            urljoin(repos[0]['_href'], 'actions/publish/'),
            {'id': cls.responses['distribute'].json()['id']},
        ))
        # Sync second repo
        sync_path = urljoin(repos[1]['_href'], 'actions/sync/')
        cls.responses['sync'].append(client.post(
            sync_path, {'override_config': {}}
        ))
        # Search for units in both repositories again
        cls.responses['units after removal'] = [
            client.post(urljoin(repo['_href'], 'search/units/'), body)
            for repo in repos
        ]
        for repo in repos:
            cls.resources.add(repo['_href'])

    @classmethod
    def tearDownClass(cls):
        """Delete created resources."""
        client = api.Client(cls.cfg)
        for resource in cls.resources:
            client.delete(resource)


class RemoveMissingTrueTestCase(_CommonTestsMixin, _BaseTestCase):
    """Test correct functionality with remove-missing option enabled."""

    @classmethod
    def setUpClass(cls):  # pylint:disable=arguments-differ
        """Create two repositories for functionality testing."""
        super(RemoveMissingTrueTestCase, cls).setUpClass(rm_missing=True)

    def test_units_after_removal(self):
        """Test that units in repositories after removal are the same."""
        bodies = [re.json() for re in self.responses['units after removal']]
        # Package category and package group will differ so we count only RPMs
        self.assertEqual(
            set(unit['unit_id'] for unit in bodies[0]
                if unit['unit_type_id'] == 'rpm'),  # This test is fragile
            set(unit['unit_id'] for unit in bodies[1]
                if unit['unit_type_id'] == 'rpm'),  # due to hard-coded
        )  # indices. But the data is complex, and this makes things simpler.
