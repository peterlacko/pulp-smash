# coding=utf-8
"""Api package contains classes for easier resource managament in pulp-smash.
"""

from __future__ import unicode_literals

import requests
import time
import string
import random
from collections  import defaultdict
from requests.exceptions import HTTPError
from pulp_smash.config import get_config

# List of all paths here
REPOSITORY_PATH = "/pulp/api/v2/repositories/"
REPOSITORY_ID_PATH = "/pulp/api/v2/repositories/" + "{}/"  # .format(<repo_id>)
POLL_TASK_PATH = "/pulp/api/v2/tasks/{}/"  # .format(<task_id>)

#  Repository related variables
REPORT_KEYS = {
    'result',
    'error',
    'spawned_tasks',
}
ERROR_KEYS = {
    '_href',
    'error',
    'error_message',
    'exception',
    'http_status',
    'traceback',
}

# Task related variables
TASK_ERROR_STATES = {
    'error',
    'timed out',
}
TASK_SUCCESS_STATES = {
    'finished',
}
TASK_RUNNING_STATES = {
    'running',
    'suspended',
    'waiting',
}


def get_random_string(length = 15):
    """Get random lowercase letters string."""
    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(0, length)
    )

class Repository(object):
    """Provides interface for easy manipulation with pulp repositories.
    `Create repo` accepts following kwarg parameters:
        .. _Create repo:
            http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/cud.html

    Each time request to server is made, ie. by calling :meth:`create_repo`
    method, response is saved to last_response variable.

    :param id: System wide unique repository identifier.
    :param display_name: User-friendly name for the repository
    :param description: User-friendly text describing the repository’s contents
    :param notes: Key-value pairs to programmatically tag the repository
    :param importer_type_id: Type id of importer being associated with the
        repository
    :param importer_config: Configuration the repository will use to drive
        the behavior of the importer
    :distributors: Array of objects containing values of distributor_type_id,
        repo_plugin_config, auto_publish, and distributor_id
        """

    def __init__(self, **kwargs):
        self.data_keys = defaultdict()
        self.data_keys.update(kwargs)
        self.last_response = None
        self.cfg = get_config()

    def create_repo(self, **kwargs):
        """Create repository on pulp server.
        After calling this method, <repo>.last_response.raise_for_status()
        should be called in order to make sure that repo was correctly created.
        :param kwargs: Additional arguments which will be passed to request,
        same as in :class:`Repository` constructor.
        """
        self.data_keys.update(kwargs)
        self.last_response = requests.post(
            self.cfg.base_url + REPOSITORY_PATH,
            json=self.data_keys,
            **self.cfg.get_requests_kwargs()
        )

    def create_rpm_repo(self, **kwargs):
        """Create RPM repository on pulp server.
        """
        if self.data_keys.get('notes') is None:
            self.data_keys['notes'] = defaultdict()
        self.data_keys['notes'].update({'_repo-type': 'rpm-repo'})
        self.create_repo(**kwargs)

    def delete_repo(self):
        """Delete repository from pulp server.
        After calling this method, <repo>.last_response.raise_for_status()
        Taks.wait_for_tasks(<repo>.last_response) should be called in order
        to make sure repo was correctly deleted.
        """
        self.last_response = requests.delete(
            self.cfg.base_url +
            REPOSITORY_ID_PATH.format(self.data_keys['id']),
            **self.cfg.get_requests_kwargs()
        )

    def get_repo(self):
        """Get information about repository on server.
        After calling this method, <repo>.last_response.raise_for_status()
        should be called in order to make sure that call was succesfull.
        """
        self.last_response = requests.get(
            self.cfg.base_url + REPOSITORY_ID_PATH.format(self.data_keys['id']),
            **self.cfg.get_requests_kwargs()
        )

    def update_repo(
        self,
        delta,
        importer_config=None,
        distributor_configs=None
    ):
        """Update repository with keys from kwargs.
        After calling this method, <repo>.last_response.raise_for_status()
        and Task.wait_for_tasks(<repo>.last_response)
        should be called in order to make sure repo was correctly updated.
        :param delta: Object containing keys with values that should
            be updated on the repository.
        :param importer_config: Object containing keys with values that should
            be updated on the repository’s importer config.
        :param distributor_configs: object containing keys that
            are distributor ids
        """
        my_delta = {'delta': delta}
        if importer_config is not None:
            my_delta.update({'importer_config': importer_config})
        if distributor_configs is not None:
            my_delta.update({'distributor_configs': distributor_configs})
        self.last_response = requests.put(
            self.cfg.base_url + REPOSITORY_ID_PATH.format(self.data_keys['id']),
            json=my_delta,
            **self.cfg.get_requests_kwargs()
        )

    # def associate_importer(self):


class Task(object):
    """Handles tasks related operations. So far only waiting for given tasks
    to immediate finish is implemented.
    """

    def __init__(self):
        self.cfg = get_config()

    def _wait_for_task(self, task, timeout, frequency):
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
                self.cfg.base_url + POLL_TASK_PATH.format(task["task_id"]),
                **self.cfg.get_requests_kwargs()
            )
            response.raise_for_status()
            # task finished (with success or failure)
            if (response.json()["state"]
                    in TASK_ERROR_STATES | TASK_SUCCESS_STATES):
                return response
        # task probably timed out

    def wait_for_tasks(self, report, timeout=120, frequency=0.5):
        """Wait for all populated tasks to finish.
        :param report: Call response -- report -- with list of populated tasks.
        :param timeout: Timeout in seconds for each task to complete.
        :param frequency: Task polling frequency in seconds.
        """
        responses = []
        # all(key in report.json().keys() for key in REPORT_KEYS):
        for task in report.json()["spawned_tasks"]:
            responses.append(self._wait_for_task(task, timeout, frequency))
