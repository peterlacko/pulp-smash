# coding=utf-8
"""Values usable by multiple test modules."""
from __future__ import unicode_literals


ERROR_KEYS = frozenset((
    '_href',
    'error',
    'error_message',
    'exception',
    'http_status',
    'traceback',
))
"""See: `Exception Handling`_.

.. _Exception Handling:
    https://pulp.readthedocs.org/en/latest/dev-guide/conventions/exceptions.html

"""

TASK_ERROR_STATES = {
    'error',
    'timed out',
}
"""See `Task Management`_.
.. _Task Management:
    http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/dispatch/task.html
"""

TASK_SUCCESS_STATES = {
    'finished',
}
"""See `Task Management`_.
.. _Task Management:
    http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/dispatch/task.html
"""

TASK_RUNNING_STATES = {
    'running',
    'suspended',
    'waiting',
}
"""See `Task Management`_.
.. _Task Management:
    http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/dispatch/task.html
"""

REPORT_KEYS = frozenset((
    'result',
    'error',
    'spawned_tasks',
))
"""See `Call Report`_.
.. _Call Report:
    http://pulp.readthedocs.org/en/latest/dev-guide/conventions/sync-v-async.html#call-report
"""

LOGIN_PATH = '/pulp/api/v2/actions/login/'
"""See: `Authentication`_.

.. _Authentication:
    https://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/authentication.html

"""

USER_PATH = '/pulp/api/v2/users/'
"""See: `User APIs`_.

.. _User APIs:
    https://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/user/index.html

"""

REPOSITORY_PATH = '/pulp/api/v2/repositories/'
"""See: `Repository API`_.
.. _Repository API:
    http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/repo/cud.html
"""

TASK_PATH = '/pulp/api/v2/tasks/'
"""See `Task Management`_.
.. _Task Management:
    http://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/dispatch/task.html
"""
