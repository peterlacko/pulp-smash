# coding=utf-8
"""Test API functionality of RPM repository."""
from __future__ import unicode_literals

from pulp_smash.resources.platform.api_v2.api import get_random_string
from pulp_smash.resources.platform.api_v2.api import Repository, Task
from pulp_smash.resources.platform.api_v2.api import ERROR_KEYS
from unittest2 import TestCase


class RPMRepoCreateSuccess(TestCase):
    """Test creating RPM repository, ie. repository containing
    {"_repo-type": "rpm-value"} pair in "notes".
    """

    @classmethod
    def setUpClass(cls):
        """Create RPM repository on pulp server."""
        cls.repo = Repository(id=get_random_string())
        cls.repo.create_rpm_repo()
        cls.task = Task()

    def test_status_code(self):
        """Test if create repo returned 201."""
        self.assertEqual(self.repo.last_response.status_code, 201)

    def test_repo_created(self):
        """Test if repo with given ID was created and if contains all keys."""
        self.assertEqual(
            self.repo.last_response.json()['id'],
            self.__class__.__name__,
            set(self.repo.last_response.json())
        )
        self.assertEqual(
            self.repo.last_response.json()['notes']['_repo-type'],
            "rpm-repo",
            set(self.repo.last_response.json())
        )

    @classmethod
    def tearDownClass(cls):
        """Delete preiously created repository."""
        cls.repo.delete_repo()
        cls.repo.last_response.raise_for_status()
        cls.task.wait_for_tasks(cls.repo.last_response)


class RPMRepoAssociateInvalidImporter(TestCase):
    """Test of associating repository with nonexistent importer."""

    @classmethod
    def setUpClass(cls):
        """Create RPM repository for consequent test."""
        cls.repo = Repository(id=get_random_string())
        cls.repo.create_rpm_repo()
        cls.repo.last_response.raise_for_status()
        cls.repo.associate_importer(
            importer_type_id='nonexistent-importer',
            importer_config={}
        )
        cls.repo.last_response.raise_for_status()
        cls.task = Task()
        cls.task.wait_for_tasks(cls.repo.last_response)

    def test_status_code(self):
        self.assertEqual(
            self.repo.last_response.status_code,
            400,
            self.repo.last_reposonse.json()
        )

    @classmethod
    def tearDownClass(cls):
        cls.repo.delete_repo()
        cls.repo.last_reposne.raise_for_status()
        cls.task.wait_for_tasks(cls.repo.last_response)
