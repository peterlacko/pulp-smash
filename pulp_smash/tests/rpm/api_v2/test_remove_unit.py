# coding utf-8
"""Test the functionality of syncing RPM repos with remove-unit option set.

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
    * when remove_missing=True, content of foo and bar is same
    * when remove_missing=False, content of foo and bar differ

"""

from __future__ import unicode_literals

try:  # try Python 3 import first
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse  # pylint:disable=C0411,E0401

import random
import unittest2

from pulp_smash import api, config, utils
from pulp_smash.constants import (
    REPOSITORY_PATH,
)

_PUBLISH_DIR = 'pulp/repos/'
_FEED_URL = 'https://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/zoo/'


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


class _BaseTestCase(unittest2.TestCase):
    """Provide a server config, and tear down created resources."""

    @classmethod
    def setUpClass(cls):
        """Provide a server config and an iterable of resources to delete."""
        cls.cfg = config.get_config()
        cls.resources = set()

    @classmethod
    def tearDownClass(cls):
        """Delete created resources."""
        client = api.Client(cls.cfg)
        for resource in cls.resources:
            client.delete(resource)


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

    def test_task_error_traceback(self):
        """Assert each task's "error" and "traceback" fields are null."""
        for action in {'sync', 'remove unit'}:
            for i, task in enumerate(self.task_bodies[action]):
                for key in {'error', 'traceback'}:
                    with self.subTest((i, key)):
                        self.assertIsNone(task[key])

    def test_task_progress_report(self):
        """Assert no task's progress report contains error details."""
        for i, task in enumerate(self.task_bodies['sync']):
            with self.subTest(i=i):
                self.assertEqual(
                    task['progress_report']['yum_importer']['content']['error_details'],  # noqa pylint:disable=line-too-long
                    []
                )

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


class _RemoveMissingTestCase(_BaseTestCase):
    """Parent class for RemoveMissingTrueTestCase and RemoveMissingFalseTestCase.

    Provides common functionality shared by both child classes.
    Following steps are executed:
        1. Create repository foo with feed, sync and publish it.
        2. Create repository bar with foo as a feed and run sync.
        3. Get content of both repositories.
        4. Remove random unit from repository foo and publish foo.
        5. Sync repository bar.
        6. Get content of both repositories.

    """

    @classmethod
    def setUpClass(cls, remove_missing=False):  # noqa pylint:disable=arguments-differ,line-too-long
        """Create two repositories, first is feed of second one."""
        super(_RemoveMissingTestCase, cls).setUpClass()
        cls.responses = {}
        cls.task_bodies = {}
        client = api.Client(cls.cfg, api.safe_handler)

        bodies = tuple((_gen_repo() for _ in range(2)))
        bodies[0]['importer_config']['feed'] = _FEED_URL
        repos = []
        repos.append(client.post(REPOSITORY_PATH, bodies[0]).json())
        sync_path = urljoin(repos[0]['_href'], 'actions/sync/')
        # Run sync and wait for the task to complete
        cls.responses['sync'] = []
        cls.responses['sync'].append(client.post(
            sync_path, {'override_config': {}}
        ))
        cls.task_bodies['sync'] = []
        cls.task_bodies['sync'] += tuple(utils.poll_spawned_tasks(
            cls.cfg, cls.responses['sync'][-1].json()))
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
        bodies[1]['importer_config']['remove_missing'] = remove_missing
        # Create and sync second repo
        repos.append(client.post(REPOSITORY_PATH, bodies[1]).json())
        sync_path = urljoin(repos[1]['_href'], 'actions/sync/')
        cls.responses['sync'].append(client.post(
            sync_path, {'override_config': {}}
        ))
        cls.task_bodies['sync'] += tuple(utils.poll_spawned_tasks(
            cls.cfg, cls.responses['sync'][-1].json()))
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
              'filters': {'unit': {'name': cls.removed_unit}}}},
        )
        cls.task_bodies['remove unit'] = []
        cls.task_bodies['remove unit'] += tuple(utils.poll_spawned_tasks(
            cls.cfg, cls.responses['remove unit'].json()))
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
        cls.task_bodies['sync'] += tuple(utils.poll_spawned_tasks(
            cls.cfg, cls.responses['sync'][-1].json()))
        # Search for units in both repositories again
        cls.responses['units after removal'] = [
            client.post(urljoin(repo['_href'], 'search/units/'), body)
            for repo in repos
        ]
        for repo in repos:
            cls.resources.add(repo['_href'])


class RemoveMissingTrueTestCase(_CommonTestsMixin, _RemoveMissingTestCase):
    """Test correct functionality with remove-missing option enabled."""

    @classmethod
    def setUpClass(cls):  # pylint:disable=arguments-differ
        """Create two repositories for functionality testing."""
        super(RemoveMissingTrueTestCase, cls).setUpClass(remove_missing=True)

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


class RemoveMissingFalseTestCase(_CommonTestsMixin, _RemoveMissingTestCase):
    """Test correct functionality with remove-missing option disabled."""

    @classmethod
    def setUpClass(cls):  # pylint:disable=arguments-differ
        """Create two repositories for functionality testing."""
        super(RemoveMissingFalseTestCase, cls).setUpClass(remove_missing=False)

    def test_units_after_removal(self):
        """Test that units of second repository did not change."""
        body_before = self.responses['units before removal'][1].json()
        body_after = self.responses['units after removal'][1].json()
        # Package category and package group will differ so we count only RPMs
        self.assertEqual(
            set(unit['unit_id'] for unit in body_before
                if unit['unit_type_id'] == 'rpm'),  # This test is fragile
            set(unit['unit_id'] for unit in body_after
                if unit['unit_type_id'] == 'rpm'),  # due to hard-coded
        )  # indices. But the data is complex, and this makes things simpler.
