# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals

import requests
from pulp_smash.helper import get_random_string, wait_for_tasks
from pulp_smash.constants import REPOSITORY_PATH, ERROR_KEYS, RPM_REPO_FEED
from unittest2 import TestCase
from pulp_smash.config import get_config


class CreateRPMRepoSuccess(TestCase):
    """Test creating RPM repository: repository containing
    {"_repo-type": "rpm-repo"} pair in "notes".
    """
    @classmethod
    def setUpClass(cls):
        """Create RPM repository on pulp server."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH,
            json={'id': cls.repo_id, 'notes': {'_repo-type': 'rpm-repo'}},
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test if Create repo returned 201."""
        self.assertEqual(
            self.last_response.status_code,
            201,
            self.last_response.json()
        )

    def test_correct_id(self):
        """Test if response contain correct repo id."""
        self.assertEqual(
            self.last_response.json()['id'],
            self.repo_id,
            self.last_response.json()
        )

    def test_correct_notes(self):
        """Test if response contain correct repo id."""
        self.assertEqual(
            self.last_response.json()['notes'],
            {'_repo-type': 'rpm-repo'},
            self.last_response.json()
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            REPOSITORY_PATH + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)


class AssociateImporter(TestCase):
    """Test `associating valid importer` to a repository_.
    .. _associating valid importer:
        http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/cud.html#associate-an-importer-to-a-repository
    """

    @classmethod
    def setUpClass(cls):
        """Create RPM repository, test it was created succesfully, and try to
        associate yum importer with it."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH,
            json={'id': cls.repo_id, 'notes': {'_repo-type': 'rpm-repo'}},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/importers/'.format(cls.repo_id),
            json={'importer_type_id': 'yum_importer', 'importer_config': {}},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.reports = wait_for_tasks(cls.last_response, cfg=cls.cfg)

    def test_task_report_count(self):
        """Test that we got exactly one task report from server."""
        self.assertEqual(
            len(self.reports),
            1,
            "Unexpected number of task reports: {}.".format(len(self.reports))
        )

    def test_task_report_result(self):
        """Test result part of task report."""
        self.assertEqual(
            self.reports[0]['result']['id'],
            'yum_importer',
            self.reports[0]
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            REPOSITORY_PATH + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)


class AssociateInvalidImporter(TestCase):
    """Test `associating nonexistant importer`_ to a repository.
    .. _associating nonexistant importer:
        http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/cud.html#associate-an-importer-to-a-repository
    """

    @classmethod
    def setUpClass(cls):
        """Create RPM repository, test it was created succesfully, and try to
        associate nonexistent importer with it."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH,
            json={'id': cls.repo_id, 'notes': {'_repo-type': 'rpm-repo'}},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/importers/'.format(cls.repo_id),
            json={'importer_type_id': 'nonexistant_importer',
                  'importer_config': {}},
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test if request correctly returned 400."""
        self.assertEqual(
            self.last_response.status_code,
            400,
            self.last_response.json()
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            REPOSITORY_PATH + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)


class AssociateImporterToUnexistantRepo(TestCase):
    """Test that `associating valid importer`_ with non existant repozitory returns
    404: Not Found
    .. _associating valid importer:
        http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/cud.html#associate-an-importer-to-a-repository
    """

    @classmethod
    def setUpClass(cls):
        """Associate yum importer with unexistant repository."""
        cls.cfg = get_config()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/importers/'.format(get_random_string()),
            json={'importer_type_id': 'yum_importer',
                  'importer_config': {}},
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test that request returned 404 Not Found."""
        self.assertEqual(
            self.last_response.status_code,
            404,
            self.last_response.json()
        )


class AssociateUnexistentDistributor(TestCase):
    """Test that `associating invalid distributor`_ to repository will return 400.
    .. _associating invalid distributor:
        http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/cud.html#associate-a-distributor-with-a-repository
    """

    @classmethod
    def setUpClass(cls):
        """Create repository and try to associate invalid distributor to it."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH,
            json={'id': cls.repo_id, 'notes': {'_repo-type': 'rpm-repo'}},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/distributors/'.format(cls.repo_id),
            json={
                'distributor_type_id': 'invalid_distributor',
                'distributor_config': {
                    'https': True,
                    'http': False,
                    'relative_url': '/tmp/{}'.format(cls.repo_id)
                }
            },
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test if request correctly returned 400."""
        self.assertEqual(
            self.last_response.status_code,
            400,
            self.last_response.json()
        )

    def test_body(self):
        """Test if request returned correct body."""
        self.assertLessEqual(
            set(ERROR_KEYS),
            set(self.last_response.json().keys()),
            self.last_response.json()
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            REPOSITORY_PATH + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)


class AssociateDistributorToUnexistantRepo(TestCase):
    """Test that `associating valid distributor`_ to non existant repository
    returns 404: Not Found
    .. _associating valid distributor:
        http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/cud.html#associate-a-distributor-with-a-repository
    """

    @classmethod
    def setUpClass(cls):
        """Associate yum distributor to unexistant repository."""
        cls.cfg = get_config()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/distributors/'.format(get_random_string()),
            json={
                'distributor_type_id': 'yum_distributor',
                'distributor_config': {
                    'https': True,
                    'http': False,
                    'relative_url': '/tmp/{}'.format(cls.repo_id)
                }
            },
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test that request returned 404 Not Found."""
        self.assertEqual(
            self.last_response.status_code,
            404,
            self.last_response.json()
        )


class AssociateDistributor(TestCase):
    """Test `associating valid distributor` to a repository_.
    .. _associating valid distributor:
        http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/cud.html#associate-a-distributor-with-a-repository
    """

    @classmethod
    def setUpClass(cls):
        """Create RPM repository, test it was created succesfully, and try to
        associate yum distributor to it."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH,
            json={'id': cls.repo_id, 'notes': {'_repo-type': 'rpm-repo'}},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/distributors/'.format(cls.repo_id),
            json={
                'distributor_type_id': 'yum_distributor',
                'distributor_config': {
                    'https': True,
                    'http': False,
                    'relative_url': '/tmp/{}'.format(cls.repo_id)
                }
            },
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test that associate distributor returned 201 status code."""
        self.assertEqual(
            self.last_response.status_code,
            201,
            self.last_response.json()
        )

    def test_body(self):
        """Test that reply has correct distributor_type_id and config values."""
        self.assertEqual(
            {
                self.last_response.json()['repo_id'],
                self.last_response.json()['distributor_type_id'],
                self.last_response.json()['config']['relative_url']
            },
            {
                self.repo_id,
                'yum_distributor',
                '/tmp/{}'.format(self.repo_id)
            },
            self.last_response.json()
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            REPOSITORY_PATH + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)


class SynchronizeRepository(TestCase):
    """Create repository with feed and `run synchronization`_ on it. Check that
    sync finished succesfully.
    .. _run synchronization:
        http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/sync.html
    """

    @classmethod
    def setUpClass(cls):
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH,
            json={
                'id': cls.repo_id,
                'notes': {'_repo-type': 'rpm-repo'}
            },
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/importers/'.format(cls.repo_id),
            json={
                'importer_type_id': 'yum_importer',
                'importer_config': {
                    'feed': RPM_REPO_FEED,
                    'verify_checksum': True
                }
            },
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/actions/sync/'.format(cls.repo_id),
            json={'override_config': {}},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.reports = wait_for_tasks(cls.last_response, cls.cfg)

    def test_task_report_count(self):
        """Test that we got exactly one task report from server."""
        self.assertEqual(
            len(self.reports),
            1,
            "Unexpected number of task reports: {}.".format(len(self.reports))
        )

    def test_repo_sync_success(self):
        """Test that sync finished with success."""
        self.assertEqual(
            self.reports[0]['result']['result'],
            'success',
            self.reports[0]
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository and remove orphaned units."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            REPOSITORY_PATH + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)
        cls.last_response = requests.delete(
            cls.cfg.base_url + "/pulp/api/v2/content/orphans/",
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.reports = wait_for_tasks(cls.last_response, cls.cfg)
        # TODO: add function to check reports


class TestDeleteOrphans(TestCase):
    """Test deleting orphans.....""""
