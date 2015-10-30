# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals

import requests

from pulp_smash.resources.helper import paths, ERROR_KEYS
from pulp_smash.resources.helper import get_random_string, wait_for_tasks
from pulp_smash.config import get_config
from unittest2 import TestCase


class RepoCreateSuccessTestCase(TestCase):
    """Tests for successfull repo creating functionality."""

    @classmethod
    def setUpClass(cls):
        """Create repo on pulp server."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + paths['REPOSITORY_PATH'],
            json={'id': cls.repo_id},
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

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            paths['REPOSITORY_PATH'] + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)


class RepoCreateMissingIdTestCase(TestCase):
    """Test create repo functionality with missing required data keys(id)."""

    @classmethod
    def setUpClass(cls):
        """Create Repository with missing required data key."""
        cls.cfg = get_config()
        cls.repo_description = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + paths['REPOSITORY_PATH'],
            json={'description': cls.repo_description},
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Check that request returned 400: invalid parameters."""
        self.assertEqual(
            self.last_response.status_code,
            400,
            self.last_response.json()
        )

    def test_body(self):
        """Test if request returned correct body."""
        self.assertLessEqual(
            ERROR_KEYS,
            set(self.last_response.json().keys()),
            self.last_response.json()
        )


class RepoExistsTestCase(TestCase):
    """Test if created repo exists on server."""

    @classmethod
    def setUpClass(cls):
        """Create repository on server with id, description and display_name,
        test correct status code and get it.
        """
        cls.cfg = get_config()
        # string representing id, disp. name and description of repo
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + paths['REPOSITORY_PATH'],
            json={
                'id': cls.repo_id,
                'display_name': cls.repo_id,
                'description': cls.repo_id
            },
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.get(
            cls.cfg.base_url +
            paths['REPOSITORY_PATH'] +
            '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test if server returned 200."""
        self.assertEqual(
            self.last_response.status_code,
            200,
            self.last_response.json()
        )

    def test_keys(self):
        """Test if repo has all attributes: id, description and display_name.
        """
        self.assertLessEqual(
            {'id', 'display_name', 'description'},
            set(self.last_response.json().keys())
        )

    def test_values(self):
        """Test if required values are correct."""
        self.assertEqual(
            {
                self.last_response.json()['id'],
                self.last_response.json()['description'],
                self.last_response.json()['display_name']
            },
            {self.repo_id, self.repo_id, self.repo_id},
            self.last_response.json()
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            paths['REPOSITORY_PATH'] + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)


class RepoDeleteTestCase(TestCase):
    """Testing succesfull repo deletion."""

    @classmethod
    def setUpClass(cls):
        """Create, delete and get repository. Raise if error occured."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + paths['REPOSITORY_PATH'],
            json={'id': cls.repo_id},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            paths['REPOSITORY_PATH'] + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.last_response = requests.get(
            cls.cfg.base_url +
            paths['REPOSITORY_PATH'] +
            '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test if request on deleted repo returned 404, Not Found."""
        self.assertEqual(
            self.last_response.status_code,
            404,
            self.last_response.json()
        )

    def test_body(self):
        """Test if body contains all data keys."""
        self.assertLessEqual(
            ERROR_KEYS,
            set(self.last_response.json().keys()),
            self.last_response.json()
        )


class RepoUpdateTestCase(TestCase):
    """Create and then update repo. Test if updates were correctly applied."""

    @classmethod
    def setUpClass(cls):
        """Create and update repo, get repo."""
        cls.cfg = get_config()
        cls.repo_id = get_random_string()
        cls.last_response = requests.post(
            cls.cfg.base_url + paths['REPOSITORY_PATH'],
            json={'id': cls.repo_id},
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        cls.delta = {
            'display_name': cls.repo_id,
            'description': cls.repo_id,
        }
        cls.last_response = requests.put(
            cls.cfg.base_url +
            paths['REPOSITORY_PATH'] +
            '{}/'.format(cls.repo_id),
            json=cls.delta,
            **cls.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test that status code of update repo call is 200."""
        self.assertEqual(
            self.last_response.status_code,
            200,
            self.last_response.json()
        )

    def test_keys(self):
        """Test that repository description and display names are correct."""
        self.assertLessEqual(
            {'id', 'display_name', 'description'},
            set(self.last_response.json()['result'].keys())
        )

    @classmethod
    def tearDownClass(cls):
        """Delete previously created repository."""
        cls.last_response = requests.delete(
            cls.cfg.base_url +
            paths['REPOSITORY_PATH'] + '{}/'.format(cls.repo_id),
            **cls.cfg.get_requests_kwargs()
        )
        cls.last_response.raise_for_status()
        wait_for_tasks(cls.last_response, cls.cfg)
