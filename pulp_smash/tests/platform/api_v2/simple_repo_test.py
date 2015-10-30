# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals

from pulp_smash.resources.platform.api_v2.api import get_random_string
from pulp_smash.resources.platform.api_v2.api import Repository, Task
from pulp_smash.resources.platform.api_v2.api import ERROR_KEYS
from unittest2 import TestCase


class RepoCreateSuccessTestCase(TestCase):
    """Tests for successfull repo creating functionality."""

    @classmethod
    def setUpClass(cls):
        """Create repo on pulp server."""
        cls.repo = Repository(id=get_random_string())
        cls.repo.create_repo()
        cls.task = Task()

    def test_status_code(self):
        """Test if Create repo returned 201."""
        self.assertEqual(self.repo.last_response.status_code, 201)

    def test_correct_id(self):
        """Test if response contain correct repo id."""
        self.assertEqual(
            self.repo.last_response.json()['id'],
            self.repo.data_keys['id'],
            set(self.repo.last_response.json())
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.repo.delete_repo()
        cls.repo.last_response.raise_for_status()
        cls.task.wait_for_tasks(cls.repo.last_response)


class RepoCreateMissingIdTestCase(TestCase):
    """Tests for repo create functionality with missing required data keys(id).
    """

    @classmethod
    def setUpClass(cls):
        """Create Repository with required data key missing."""
        cls.repo = Repository(display_name=get_random_string())
        cls.repo.create_repo()

    def test_status_code(self):
        """Check that request returned 400: invalid parameters."""
        self.assertEqual(
            self.repo.last_response.status_code,
            400,
            self.repo.last_response.json()
        )

    def test_body(self):
        """Test if request returned correct body."""
        self.assertLessEqual(
            ERROR_KEYS,
            set(self.repo.last_response.json().keys()),
            self.repo.last_response.json()
        )


class RepoExistsTestCase(TestCase):
    """Test if created repo exists on server."""

    @classmethod
    def setUpClass(cls):
        """Create repository on server with id, description and display_name,
        test correct status code and get it.
        """
        cls.repo = Repository(
            id=get_random_string(),
            display_name=get_random_string(),
            description=get_random_string()
            )
        cls.repo.create_repo()
        cls.repo.last_response.raise_for_status()
        cls.repo.get_repo()
        cls.task = Task()

    def test_status_code(self):
        """Test if server returned 200."""
        self.assertEqual(
            self.repo.last_response.status_code,
            200,
            self.repo.last_response.json()
        )

    def test_body(self):
        """Test if repo has all set attributes: id, description and display_name.
        """
        self.assertLessEqual(
            self.repo.last_response.json().keys(),
            {'id', 'display_name', 'description'}
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.repo.delete_repo()
        cls.repo.last_response.raise_for_status()
        cls.task = Task()
        cls.task.wait_for_tasks(cls.repo.last_response)


class RepoDeleteTestCase(TestCase):
    """Testing succesfull repo deletion."""

    @classmethod
    def setUpClass(cls):
        """Create repository and raise if not created."""
        cls.repo = Repository(id=get_random_string())
        cls.repo.create_repo()
        cls.repo.last_response.raise_for_status()
        cls.repo.delete_repo()
        cls.repo.get_repo()

    def test_status_code(self):
        """Test if request on deleted repo returned 404, Not Found."""
        self.assertEqual(
            self.repo.last_response.status_code,
            404,
            self.repo.last_response.json()
        )

    def test_body(self):
        """Test if body contains all data keys."""
        self.assertLessEqual(
            ERROR_KEYS,
            set(self.repo.last_response.json().keys()),
            self.repo.last_response.json()
        )


class RepoUpdateTestCase(TestCase):
    """Create and then update repo. Test if updates were applied."""

    @classmethod
    def setUpClass(cls):
        """Create and update repo, get repo."""
        cls.repo = Repository(id=get_random_string())
        cls.repo.create_repo()
        cls.repo.last_response.raise_for_status()
        delta = {
            'display_name': get_random_string(),
            'description': get_random_string(),
        }
        cls.repo.update_repo(delta)
        cls.task = Task()

    def test_status_code(self):
        """Test that status code of update repo call is 200."""
        self.assertEqual(
            self.repo.last_response.status_code,
            200,
            self.repo.last_response.json()
        )

    def test_body(self):
        """Test that repository description and display names are correct."""
        self.assertLessEqual(
            {'id', 'display_name', 'description'},
            set(self.repo.last_response.json()['result'].keys())
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.repo.delete_repo()
        cls.repo.last_response.raise_for_status()
        cls.task.wait_for_tasks(cls.repo.last_response)
