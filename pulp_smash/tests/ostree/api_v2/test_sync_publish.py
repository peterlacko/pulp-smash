# coding=utf-8
"""Test the API endpoints for ostree repos.
Tested on pulp 2.7 release only.
Done:
    * Create repo
    * Sync repo with invalid feed or branch will fail
    * Create repo with valid feed and branch, add another branch and sync
    * Create and sync repo, copy its content to another repo, check they match
TODO:
    * Test that all branches were synced
    * Test updating a valid feed with an invalid branch
    * Extend tests of responses
    * Download and verify content
"""

from __future__ import unicode_literals

import requests

from itertools import chain
from pulp_smash.config import get_config
from pulp_smash.utils import (
    create_repository,
    delete,
    get_importers,
    handle_response,
    poll_spawned_tasks,
    sync_repository,
    uuid4,
)
from unittest2 import TestCase
from urlparse import urljoin

_VALID_FEED = "http://dl.fedoraproject.org/pub/fedora/linux/atomic/23/"
_VALID_BRANCH1 = "fedora-atomic/f23/x86_64/docker-host"
_VALID_BRANCH2 = "fedora-atomic/f23/x86_64/testing/docker-host"


class _BaseTestCase(TestCase):
    """Provide a server config, and tear down created resources."""

    @classmethod
    def setUpClass(cls):
        """Provide a server config and an iterable of resources to delete."""
        cls.cfg = get_config()
        cls.attrs_iter = tuple()

    @classmethod
    def tearDownClass(cls):
        """Delete created resources."""
        for attrs in cls.attrs_iter:
            delete(cls.cfg, attrs['_href'])


def _gen_ostree_repo_body():
    """Return ostree repo body.

    """
    return {
        'id': uuid4(),
        'importer_type_id': 'ostree_web_importer',
        'importer_config': {},
        'distributors': [],
        'notes': {'_repo-type': 'OSTREE'},
    }


def _add_ostree_web_distributor(server_config, href, responses=None):
    """Add ostree distributor."""

    return handle_response(requests.post(
        urljoin(server_config.base_url, href + 'distributors/'),
        json={
            'auto_publish': False,
            'distributor_id': uuid4(),
            'distributor_type_id': 'ostree_web_distributor',
            'distributor_config': {
                'http': True,
                'https': True,
                'relative_url': '/' + uuid4(),
            },
        },
        **server_config.get_requests_kwargs()
    ), responses)


def _copy_repo(server_config, source_repo_id, href, responses=None):
    """Copy content from one repository to another.

    :param server_config: A :class:`pulp_smash.config.ServerConfig` object.
    :param source_repo_id: A string. The ID of the source repository.
    :param href: A string. The path to the repository on which the association
        action is being performed. Content is copied to this repo.
    :param responses: A list, or some other object that supports the ``append``
        method. If given, all server responses are appended to this object.
    :returns: The server's JSON-decoded response.

    """
    return handle_response(requests.post(
        urljoin(server_config.base_url, href + 'actions/associate/'),
        json={'source_repo_id': source_repo_id},
        **server_config.get_requests_kwargs()
    ), responses)


def _get_units(server_config, href, responses=None):
    """Search for a repository's units."""
    return handle_response(requests.post(
        urljoin(server_config.base_url, href + 'search/units/'),
        json={'criteria': {}},
        **server_config.get_requests_kwargs()
    ), responses)


def _update_branch(server_config, href, branch, responses=None):
    """Add new branch to ostree repo with feed."""
    return handle_response(requests.put(
        urljoin(server_config.base_url, href),
        json={'importer_config': {
            'branches': [branch]},
            'delta': {'bg': False}
        },
        **server_config.get_requests_kwargs()
    ), responses)


class CreateTestCase(_BaseTestCase):
    """Create two ostree repositories, with and without feed."""

    @classmethod
    def setUpClass(cls):
        """Create two repositories."""
        super(CreateTestCase, cls).setUpClass()
        cls.bodies = tuple((_gen_ostree_repo_body() for _ in range(2)))
        cls.bodies[1]['importer_config'] = {'feed': uuid4()}  # should pass??
        cls.attrs_iter = tuple((
            create_repository(cls.cfg, body) for body in cls.bodies
        ))
        cls.importers_iter = tuple((
            get_importers(cls.cfg, attrs['_href']) for attrs in cls.attrs_iter
        ))

    def test_id_notes(self):
        """Validate the ``id`` and ``notes`` attributes for each repo."""
        for key in ('id', 'notes'):
            for body, attrs in zip(self.bodies, self.attrs_iter):
                with self.subTest((key, body, attrs)):
                    self.assertIn(key, attrs)
                    self.assertEqual(body[key], attrs[key])

    def test_number_importers(self):
        """Each repository should have only one importer."""
        for i, importers in enumerate(self.importers_iter):
            with self.subTest(i=i):
                self.assertEqual(len(importers), 1, importers)

    def test_importer_type_id(self):
        """Validate the ``importer_type_id`` attribute of each importer."""
        key = 'importer_type_id'
        for body, importers in zip(self.bodies, self.importers_iter):
            with self.subTest((body, importers)):
                self.assertIn(key, importers[0])
                self.assertEqual(body[key], importers[0][key])

    def test_importer_config(self):
        """Validate the ``config`` attribute of each importer."""
        key = 'config'
        for body, importers in zip(self.bodies, self.importers_iter):
            with self.subTest((body, importers)):
                self.assertIn(key, importers[0])
                self.assertEqual(body['importer_' + key], importers[0][key])


class SyncUpdateValidFeedTestCase(_BaseTestCase):
    """If a valid feed is given, the sync completes with no reported errors.

    """

    @classmethod
    def setUpClass(cls):
        """Create an OSTree repository with a valid feed and sync it."""
        super(SyncUpdateValidFeedTestCase, cls).setUpClass()
        body = _gen_ostree_repo_body()
        body['importer_config']['feed'] = _VALID_FEED
        body['importer_config']['branches'] = [_VALID_BRANCH1]
        cls.attrs_iter = (create_repository(cls.cfg, body),)  # see parent cls
        # update 'refs' with new branch
        cls.update_branch = []
        _update_branch(
            cls.cfg,
            cls.attrs_iter[0]['_href'],
            _VALID_BRANCH2,
            cls.update_branch,
        )

        cls.sync_repo = []  # raw responses
        report = sync_repository(
            cls.cfg,
            cls.attrs_iter[0]['_href'],
            cls.sync_repo,
        )
        cls.task_bodies = tuple(poll_spawned_tasks(cls.cfg, report))

    def test_start_sync_code(self):
        """Assert the call to sync a repository returns an HTTP 202."""
        self.assertEqual(self.sync_repo[0].status_code, 202)

    def test_update_code(self):
        """Assert that branch update on repository returns an HTTP 200."""
        self.assertEqual(self.update_branch[0].status_code, 200)

    def test_task_error(self):
        """Assert each task's "error" field is null."""
        for i, task_body in enumerate(self.task_bodies):
            with self.subTest(i=i):
                self.assertEqual(task_body['error'], None)

    def test_task_traceback(self):
        """Assert each task's "traceback" field is null."""
        for i, task_body in enumerate(self.task_bodies):
            with self.subTest(i=i):
                self.assertEqual(task_body['traceback'], None)

    def test_task_progress_report(self):
        """Assert no task's progress report contains error details."""
        for i, task_body in enumerate(self.task_bodies):
            for action in task_body['progress_report']['ostree_web_importer']:
                with self.subTest(i=i):
                    self.assertEqual(
                        len(action['error_details']),
                        0
                    )


class SyncInvalidFeedBranchTestCase(_BaseTestCase):
    """With invalid feed or branch, the sync completes with reported errors."""

    @classmethod
    def setUpClass(cls):
        """Create an OSTree repository with an invalid feed and sync it."""
        super(SyncInvalidFeedBranchTestCase, cls).setUpClass()
        bodies = tuple(_gen_ostree_repo_body() for _ in range(2))
        bodies[0]['importer_config']['feed'] = uuid4()  # invalid feed
        bodies[0]['importer_config']['branches'] = [_VALID_BRANCH1]
        bodies[1]['importer_config']['feed'] = _VALID_FEED
        bodies[1]['importer_config']['branches'] = [uuid4()]  # invalid branch
        cls.attrs_iter = (create_repository(cls.cfg, body) for body in bodies)
        cls.sync_repos = []  # raw responses
        reports = tuple(sync_repository(
            cls.cfg,
            attr_iter['_href'],
            cls.sync_repos,
        ) for attr_iter in cls.attrs_iter)
        cls.task_bodies = tuple(chain.from_iterable(
            poll_spawned_tasks(cls.cfg, report) for report in reports
        ))

    def test_start_sync_code(self):
        """Assert the call to sync a repository returns an HTTP 202."""
        for sync_repo in self.sync_repos:
            with self.subTest(sync_repo=sync_repo):
                self.assertEqual(sync_repo.status_code, 202)

    def test_task_error(self):
        """Assert each task's "error" field is non-null."""
        for i, task_body in enumerate(self.task_bodies):
            with self.subTest(i=i):
                self.assertIsNotNone(task_body['error'])

    def test_task_traceback(self):
        """Assert each task's "traceback" field is non-null."""
        for i, task_body in enumerate(self.task_bodies):
            with self.subTest(i=i):
                self.assertIsNotNone(task_body['traceback'])

    def test_error_details(self):
        """Assert each task's progress report contains error details."""
        for i, task_body in enumerate(self.task_bodies):
            for action in task_body['progress_report']['ostree_web_importer']:
                with self.subTest(i=i):
                    if action['step_type'] == 'import_pull':  # import fails
                        self.assertNotEqual(
                            action['error_details'],
                            [],
                            action,
                        )
                    # create_repository finishes with success
                    # import_add_unit, import_clean do not start
                    else:
                        self.assertEqual(
                            action['error_details'],
                            [],
                            action,
                        )

    def test_number_tasks(self):
        """Assert that two task were spawned."""
        self.assertEqual(len(self.task_bodies), 2)


class SyncCopyValidFeedTestCase(_BaseTestCase):
    """Create two repos, sync, copy, publish (automatically), check"""

    @classmethod
    def setUpClass(cls):
        """Create an OSTree repository with a valid feed and sync it.

        Create 2 repos, one with feed. Sync one, copy to another, publish,
        check.
        """
        steps = {
            'sync',
            'copy',
            'search units',
        }
        cls.responses = {key: [] for key in steps}
        cls.bodies = {}
        cls.task_bodies = {}

        super(SyncCopyValidFeedTestCase, cls).setUpClass()
        bodies = tuple(_gen_ostree_repo_body() for _ in range(2))
        bodies[0]['importer_config']['feed'] = _VALID_FEED
        bodies[0]['importer_config']['branches'] = [_VALID_BRANCH1]
        cls.attrs_iter = tuple(create_repository(cls.cfg, body)
                               for body in bodies)
        cls.bodies['sync'] = sync_repository(
            cls.cfg,
            cls.attrs_iter[0]['_href'],
            cls.responses['sync'],
        )
        cls.task_bodies['sync'] = tuple(poll_spawned_tasks(
            cls.cfg, cls.bodies['sync']))
        # copy content from repo #0 to repo #1
        print cls.attrs_iter[0]['_href']
        print cls.attrs_iter[1]['_href']
        cls.bodies['copy'] = _copy_repo(
            cls.cfg,
            cls.attrs_iter[0]['id'],
            cls.attrs_iter[1]['_href'],
            cls.responses['copy'],
        )
        cls.task_bodies['copy'] = tuple(poll_spawned_tasks(
            cls.cfg, cls.bodies['copy']))
        # search for content in both repositories
        cls.bodies['search units'] = tuple((
            _get_units(cls.cfg, attrs['_href'], cls.responses['search units'])
            for attrs in cls.attrs_iter
        ))
        # print "Search units returned: ", cls.bodies['search units']

    def test_start_sync_code(self):
        """Assert the call to sync a repository returns an HTTP 202."""
        steps_codes = (
            ('sync', 202),
            ('copy', 202),
            ('search units', 200),
        )
        for step, code in steps_codes:
            with self.subTest((step, code)):
                for response in self.responses[step]:
                    self.assertEqual(response.status_code, code)

    def test_task_error(self):
        """Assert each task's "error" field is null."""
        for step in {'sync', 'copy'}:
            for i, task_body in enumerate(self.task_bodies[step]):
                with self.subTest(i=i):
                    self.assertEqual(task_body['error'], None)

    def test_task_traceback(self):
        """Assert each task's "traceback" field is null."""
        for step in {'sync', 'copy'}:
            for i, task_body in enumerate(self.task_bodies[step]):
                with self.subTest(i=i):
                    self.assertEqual(task_body['traceback'], None)

    def test_task_progress_report(self):
        """Assert no task's progress report contains error details."""
        for i, task_body in enumerate(self.task_bodies['sync']):
            for action in task_body['progress_report']['ostree_web_importer']:
                with self.subTest(i=i):
                    self.assertEqual(
                        len(action['error_details']),
                        0
                    )

    def test_search_units(self):
        """Verify the two repositories have the same units."""
        self.assertEqual(
            set(unit['unit_id'] for unit in self.bodies['search units'][0]),
            set(unit['unit_id'] for unit in self.bodies['search units'][1]),
        )
