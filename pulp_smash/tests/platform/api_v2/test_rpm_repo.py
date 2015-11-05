# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals

from pulp_smash.helper import get_random_string, wait_for_tasks
from pulp_smash.constants import ERROR_KEYS, REPOSITORY_PATH
from unittest2 import TestCase

class RPMRepoCreateSuccess(TestCase):
    """Test creating RPM repository: repository containing
    {"_repo-type": "rpm-value"} pair in "notes".
    """
