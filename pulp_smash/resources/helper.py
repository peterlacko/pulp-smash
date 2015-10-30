# coding=utf-8
"""Test for basic repo creating functionality."""
from __future__ import unicode_literals

import string
import random
import time
import requests

paths = {
    'REPOSITORY_PATH': '/pulp/api/v2/repositories/',
    'TASK_PATH': '/pulp/api/v2/tasks/',
}

#  Repository related variables
ERROR_KEYS = {
    '_href',
    'error',
    'error_message',
    'exception',
    'http_status',
    'traceback',
}

# Task related variables
REPORT_KEYS = {
    'result',
    'error',
    'spawned_tasks',
}

task_states = {
    'TASK_ERROR_STATES': {
        'error',
        'timed out',
    },
    'TASK_SUCCESS_STATES': {
        'finished',
    },
    'TASK_RUNNING_STATES': {
        'running',
        'suspended',
        'waiting',
    }
}


def get_random_string(length=15):
    """Get random lowercase letters string."""
    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(0, length)
    )


def _wait_for_task(task, cfg, timeout, frequency):
    """Wait for single task to finish its execution on server.
    :param task: Dictionary containtin task_id and path to task
        on pulp server.
    :param timeout: Timeout in seconds for each task to complete.
    :param frequency: Task polling frequency in seconds.
    """
    task_timeout = time.time() + timeout
    while time.time() <= task_timeout:
        time.sleep(frequency)
        response = requests.get(
            (
                cfg.base_url +
                paths['TASK_PATH'] +
                '{}/'.format(task["task_id"])
            ),
            **cfg.get_requests_kwargs()
        )
        response.raise_for_status()
        # task finished (with success or failure)
        if (
            response.json()['state']
            in task_states['TASK_ERROR_STATES'] |
            task_states['TASK_SUCCESS_STATES']
        ):
            return response
    # task probably timed out


def wait_for_tasks(report, cfg, timeout=120, frequency=0.5):
    """Wait for all populated tasks to finish.
    :param report: Call response -- report -- with list of populated tasks.
    :param timeout: Timeout in seconds for each task to complete.
    :param frequency: Task polling frequency in seconds.
    :return: List of tasks and their states
    """
    responses = []
    # all(key in report.json().keys() for key in REPORT_KEYS):
    for task in report.json()["spawned_tasks"]:
        responses.append(_wait_for_task(task, cfg, timeout, frequency))
    return responses
