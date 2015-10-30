# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals

import string
import random

paths = {
    'REPOSITORY_PATH': '/pulp/api/v2/repositories/',
    'TASK_PATH': '/pulp/api/v2/tasks/',
}


def get_random_string(length=15):
    """Get random lowercase letters string."""
    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(0, length)
    )
