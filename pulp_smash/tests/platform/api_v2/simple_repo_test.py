# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals


class RepoCreateSuccessTestCase(TestCase):
    """Tests for successfull repo creating functionality."""

    @classmethod
    def setUpClass(cls):
        """Create repo on pulp server."""
        cls.repo = Repository(id=cls.__name__)
        cls.repo.create_repo()

    def test_status_code(self):
        """Test if Create repo returned 201."""
        self.assertEqual(self.repo.last_response.status_code, 201)

    def test_correct_id(self):
        """Test if response contain correct repo id."""
        self.assertEqual(
            self.repo.last_response.json()['id'],
            self.__class__.__name__,
            set(self.repo.last_response.json()))

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.repo.delete_repo()
        cls.repo.last_response.raise_for_status()
        Task.wait_for_tasks(cls.repo.last_response)
