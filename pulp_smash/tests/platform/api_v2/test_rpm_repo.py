# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals

import requests
from pulp_smash.helper import get_random_string, wait_for_tasks
from pulp_smash.constants import REPOSITORY_PATH
from unittest2 import TestCase
from pulp_smash.config import get_config


class RPMRepoCreateSuccess(TestCase):
    """Test creating RPM repository: repository containing
    {"_repo-type": "rpm-value"} pair in "notes".
    """
    @classmethod
    def setUpClass(cls):
        """Create RPM repository on pulp server."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH,
            json={'id': cls.repo_id, 'notes': {'_repo_type': 'rpm-value'}},
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
            {'_repo_type': 'rpm-value'},
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


class RPMRepoAssociateImporter(TestCase):
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
            json={'id': cls.repo_id, 'notes': {'_repo_type': 'rpm-value'}},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.post(
            cls.cfg.base_url + REPOSITORY_PATH +
            '{}/importers/'.format(cls.repo_id),
            json={'importer_type_id': 'yum_importer',
                  'importer_config' : {}},
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


class RPMRepoAssociateInvalidImporter(TestCase):
    """Test `associating nonexistant importer` to a repository_.
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
            json={'id': cls.repo_id, 'notes': {'_repo_type': 'rpm-value'}},
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
