# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals

import requests

from pulp_smash.resources.helper import get_random_string
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
            self.cfg.base_url + paths['REPOSITORY_PATH'],
            json=cls.repo_id,
            **self.cfg.get_requests_kwargs()
        )

    def test_status_code(self):
        """Test if Create repo returned 201."""
        self.assertEqual(self.last_response.status_code, 201)

    def test_correct_id(self):
        """Test if response contain correct repo id."""
        self.assertEqual(
            self.last_response.json()['id'],
            self.repo_id,
            self.last_response.json()
        )
