# coding=utf-8
"""Test Pulp's `Searching`_ facilities.

The tests in this module make use of the `User APIs`_. However, few
user-specific references are made. These tests could be rewritten to use
repositories or something else with only minimal changes. Thus, the name of
this module.

Each test case executes one or more pairs of semantically identical POST and
GET requests. Each pair of search results should match exactly.

Most test cases assume that the assertions in some other test case hold true.
The assumptions explored in this module have the following dependencies::

    It is possible to ask for all resources of a kind.
    ├── It is possible to sort search results.
    ├── It is possible to ask for a single field in search results.
    ├── It is possible to ask for several fields in search results.
    └── It is possible to ask for a resource with a specific ID.
        └── It is possible to ask for a resource with one of several IDs.
            ├── It is possible to skip some search results.
            └── It is possible to limit how many search results are returned.

.. _Searching:
    https://pulp.readthedocs.org/en/latest/dev-guide/conventions/criteria.html
.. _User APIs:
    https://pulp.readthedocs.org/en/latest/dev-guide/integration/rest-api/user/index.html
"""
from __future__ import unicode_literals

import random

import unittest2

from pulp_smash import api, config
from pulp_smash.constants import USER_PATH
from pulp_smash.utils import uuid4


_SEARCH_PATH = USER_PATH + 'search/'


def _create_users(server_config, num):
    """Create ``num`` users with random logins. Return tuple of attributes."""
    client = api.Client(server_config, api.json_handler)
    users = (client.post(USER_PATH, {'login': uuid4()}) for _ in range(num))
    return tuple(users)


class _BaseTestCase(unittest2.TestCase):
    """Provide a server config to tests, and delete created resources."""

    @classmethod
    def setUpClass(cls):
        """Provide a server config and an empty set of resources to delete."""
        cls.cfg = config.get_config()
        cls.resources = set()  # a set of _href paths
        cls.searches = {}

    def test_status_code(self):
        """Assert each search has an HTTP 200 status code."""
        for key, response in self.searches.items():
            with self.subTest(key=key):
                self.assertEqual(response.status_code, 200)

    @classmethod
    def tearDownClass(cls):
        """For each resource in ``cls.resources``, delete that resource."""
        client = api.Client(cls.cfg)
        for resource in cls.resources:
            client.delete(resource)


class MinimalTestCase(_BaseTestCase):
    """Ask for all resources of a certain kind.

    ==== ====
    GET  no query parameters
    POST ``{'criteria': {}}``
    ==== ====
    """

    @classmethod
    def setUpClass(cls):
        """Create one user. Execute searches."""
        super(MinimalTestCase, cls).setUpClass()
        client = api.Client(cls.cfg)
        cls.user = _create_users(cls.cfg, 1)[0]
        cls.searches = {
            'get': client.get(_SEARCH_PATH),
            'post': client.post(_SEARCH_PATH, {'criteria': {}}),
        }
        cls.resources.add(cls.user['_href'])  # mark for deletion

    def test_user_found(self):
        """Assert each search should include the user we created."""
        for key, response in self.searches.items():
            with self.subTest(key=key):
                logins = {user['login'] for user in response.json()}
                self.assertIn(self.user['login'], logins)


class SortTestCase(_BaseTestCase):
    """Ask for sorted search results.

    There is no specification for executing these searches with GET.

    ==== ====
    POST ``{'criteria': {'sort': [['id', 'ascending']]}}``
    POST ``{'criteria': {'sort': [['id', 'descending']]}}``
    ==== ====
    """

    @classmethod
    def setUpClass(cls):
        """Create two users. Execute searches."""
        super(SortTestCase, cls).setUpClass()
        cls.resources = {user['_href'] for user in _create_users(cls.cfg, 2)}
        client = api.Client(cls.cfg)
        for order in {'ascending', 'descending'}:
            json = {'criteria': {'sort': [['id', order]]}}
            cls.searches['post_' + order] = client.post(_SEARCH_PATH, json)

    def test_ascending(self):
        """Assert ascending results are ordered from low to high."""
        results = self.searches['post_ascending'].json()
        ids = [result['_id']['$oid'] for result in results]
        self.assertEqual(ids, sorted(ids))

    def test_descending(self):
        """Assert descending results are ordered from high to low."""
        results = self.searches['post_descending'].json()
        ids = [result['_id']['$oid'] for result in results]
        self.assertEqual(ids, sorted(ids, reverse=True))


@unittest2.skip('See: https://pulp.plan.io/issues/1332')
class FieldTestCase(_BaseTestCase):
    """Ask for a single field in search results.

    ==== ====
    GET  ``{'field': 'name'}`` (urlencoded)
    POST ``{'criteria': {'fields': 'name'}}``
    ==== ====
    """

    @classmethod
    def setUpClass(cls):
        """Create one user. Execute searches."""
        super(FieldTestCase, cls).setUpClass()
        cls.resources = {_create_users(cls.cfg, 1)[0]['_href']}
        client = api.Client(cls.cfg)
        cls.searches = {
            'get': client.get(_SEARCH_PATH, params={'field': 'name'}),
            'post': client.post(
                _SEARCH_PATH,
                {'criteria': {'fields': ['name']}},
            )
        }

    def test_field(self):
        """Only the requested key should be in each response."""
        for method, response in self.searches.items():
            with self.subTest(method=method):
                for result in response.json():  # for result in results:
                    self.assertEqual(set(result.keys()), {'name'})


@unittest2.skip('See: https://pulp.plan.io/issues/1332')
class FieldsTestCase(_BaseTestCase):
    """Ask for several fields in search results.

    ==== ====
    GET  ``field=login&field=roles``
    POST ``{'criteria': {'fields': ['login', 'roles']}}``
    ==== ====
    """

    @classmethod
    def setUpClass(cls):
        """Create one user. Execute searches."""
        super(FieldsTestCase, cls).setUpClass()
        cls.resources = {_create_users(cls.cfg, 1)[0]['_href']}
        client = api.Client(cls.cfg)
        cls.searches = {
            'get': client.get(_SEARCH_PATH, params='?field=login&field=roles'),
            'post': client.post(
                _SEARCH_PATH,
                {'criteria': {'fields': ['login', 'roles']}},
            ),
        }

    def test_fields(self):
        """Only the requested keys should be in each response."""
        for action, response in self.searches.items():
            with self.subTest(action=action):
                for result in response.json():  # for result in results:
                    self.assertEqual(set(result.keys()), {'login', 'roles'})


class FiltersIdTestCase(_BaseTestCase):
    """Ask for a resource with a specific ID.

    There is no specification for executing these searches with GET.

    ==== ====
    GET  ``{'filters': {'id': '…'}}`` (urlencoded)
    POST ``{'criteria': {'filters': {'id': '…'}}}``
    ==== ====
    """

    @classmethod
    def setUpClass(cls):
        """Create two users. Search for one user."""
        super(FiltersIdTestCase, cls).setUpClass()
        users = _create_users(cls.cfg, 2)
        cls.resources = {user['_href'] for user in users}
        cls.user = random.choice(users)  # search for this user
        json = {'criteria': {'filters': {'id': cls.user['id']}}}
        cls.searches['post'] = api.Client(cls.cfg).post(_SEARCH_PATH, json)

    def test_result_ids(self):
        """Assert the search results contain the correct IDs."""
        for method, response in self.searches.items():
            with self.subTest(method=method):
                ids = {result['_id']['$oid'] for result in response.json()}
                self.assertEqual({self.user['id']}, ids)


class FiltersIdsTestCase(_BaseTestCase):
    """Ask for resources with one of several IDs.

    There is no specification for executing these searches with GET.

    ==== ====
    GET  ``{'filters': {'id': {'$in': ['…', '…']}}}``
    POST ``{'criteria': {'filters': {'id': {'$in': ['…', '…']}}}}``
    ==== ====
    """

    @classmethod
    def setUpClass(cls):
        """Create three users. Search for two users."""
        super(FiltersIdsTestCase, cls).setUpClass()
        users = _create_users(cls.cfg, 3)
        cls.resources = {user['_href'] for user in users}
        cls.user_ids = [user['id'] for user in random.sample(users, 2)]  # noqa pylint:disable=unsubscriptable-object
        cls.searches['post'] = api.Client(cls.cfg).post(
            _SEARCH_PATH,
            {'criteria': {'filters': {'id': {'$in': cls.user_ids}}}},
        )

    def test_result_ids(self):
        """Assert the search results contain the correct IDs."""
        for method, response in self.searches.items():
            with self.subTest(method=method):
                ids = {result['_id']['$oid'] for result in response.json()}
                self.assertEqual(set(self.user_ids), ids)


class LimitSkipTestCase(_BaseTestCase):
    """Ask for search results to be limited or skipped.

    There is no specification for executing these searches with GET.

    ==== ====
    GET  ``{'filters': {'id': {'$in': [id1, id2]}}, 'limit': 1}``
    GET  ``{'filters': {'id': {'$in': [id1, id2]}}, 'skip': 1}``
    POST ``{'criteria': {'filters': {'id': {'$in': [id1, id2]}}, 'limit': 1}}``
    POST ``{'criteria': {'filters': {'id': {'$in': [id1, id2]}}, 'skip': 1}}``
    ==== ====
    """

    @classmethod
    def setUpClass(cls):
        """Create two users. Execute searches."""
        super(LimitSkipTestCase, cls).setUpClass()
        users = _create_users(cls.cfg, 2)
        cls.resources = {user['_href'] for user in users}
        cls.user_ids = [user['id'] for user in users]
        client = api.Client(cls.cfg)
        for criterion in {'limit', 'skip'}:
            key = 'post_' + criterion
            query = {'filters': {'id': {'$in': cls.user_ids}}, criterion: 1}
            cls.searches[key] = client.post(_SEARCH_PATH, {'criteria': query})

    def test_results(self):
        """Check that one of the two created users has been found."""
        for key, response in self.searches.items():
            with self.subTest(key=key):
                ids = [result['_id']['$oid'] for result in response.json()]
                self.assertEqual(len(ids), 1, ids)
                self.assertIn(ids[0], self.user_ids)
