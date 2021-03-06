# coding=utf-8
"""Tests for Pulp's "broker reconnect" feature.

Tests for `#55 <https://github.com/PulpQE/pulp-smash/issues/55>`_:

> Pulp offers a collection of behaviors known as "reconnect support" for the
> Pulp Broker. Here are the expected behaviors:
>
> * If you start a Pulp service that connects to the broker and the broker is
>   not running or is not network accessible for some reason, the Pulp services
>   will wait-and-retry. It has a backoff behavior, but the important part is
>   that Pulp services don't exit if they can't connect due to availability,
>   and when the availability problem is resolved, the Pulp services reconnect.
> * If you have a Pulp service connected to the broker and the broker shuts
>   down, the Pulp services need the wait-and-retry as described above. Once
>   the broker becomes available again the Pulp services should reconnect.

There are two scenarios to test here:

* support for initially connecting to a broker, and
* support for reconnecting to a broker that goes missing.

Both scenarios are executed by
:class:`pulp_smash.tests.rpm.api_v2.test_broker.BrokerTestCase`.
"""
from __future__ import unicode_literals

import time
try:  # try Python 3 import first
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin  # pylint:disable=C0411,E0401

import unittest2

from pulp_smash import api, cli, config, utils
from pulp_smash.constants import PULP_SERVICES, REPOSITORY_PATH


_FEED_URL = 'https://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/zoo/'
_RPM = 'bear-4.1-1.noarch.rpm'


def _gen_repo():
    """Return a semi-random dict for use in creating an RPM repostirory."""
    return {
        'id': utils.uuid4(),
        'importer_config': {'feed': _FEED_URL},
        'importer_type_id': 'yum_importer',
        'notes': {'_repo-type': 'rpm-repo'},
    }


def _gen_distributor():
    """Return a semi-random dict for use in creating a YUM distributor."""
    return {
        'auto_publish': False,
        'distributor_id': utils.uuid4(),
        'distributor_type_id': 'yum_distributor',
        'distributor_config': {
            'http': True,
            'https': True,
            'relative_url': utils.uuid4() + '/',
        },
    }


class BrokerTestCase(unittest2.TestCase):
    """Test Pulp's support for broker connections and reconnections."""

    def setUp(self):
        """Provide a server config and Pulp services to stop and start."""
        self.cfg = config.get_config()
        self.broker = utils.get_broker(self.cfg)
        self.services = tuple((
            cli.Service(self.cfg, service) for service in PULP_SERVICES
        ))

    def tearDown(self):
        """Ensure Pulp services are running."""
        for service in self.services + (self.broker,):
            service.start()

    def test_broker_connect(self):
        """Test Pulp's support for initially connecting to a broker.

        Do the following:

        1. Stop both the broker and several other services.
        2. Start the several other resources, wait, and start the broker.
        3. Test Pulp's health. Create an RPM repository, sync it, add a
           distributor, publish it, and download an RPM.
        """
        # Step 1 and 2.
        for service in self.services + (self.broker,):
            service.stop()
        for service in self.services:
            service.start()
        time.sleep(15)  # Let services try to connect to the dead broker.
        self.broker.start()
        self.health_check()  # Step 3.

    def test_broker_reconnect(self):
        """Test Pulp's support for reconnecting to a broker that goes missing.

        Do the following:

        1. Start both the broker and several other services.
        2. Stop the broker, wait, and start it again.
        3. Test Pulp's health. Create an RPM repository, sync it, add a
           distributor, publish it, and download an RPM.
        """
        # We assume that the broker and other services are already running. As
        # a result, we skip step 1 and go straight to step 2.
        self.broker.stop()
        time.sleep(30)
        self.broker.start()
        self.health_check()  # Step 3.

    def health_check(self):
        """Execute step three of the test plan."""
        client = api.Client(self.cfg, api.json_handler)
        repo = client.post(REPOSITORY_PATH, _gen_repo())
        self.addCleanup(api.Client(self.cfg).delete, repo['_href'])
        client.post(
            urljoin(repo['_href'], 'actions/sync/'),
            {'override_config': {}},
        )
        distributor = client.post(
            urljoin(repo['_href'], 'distributors/'),
            _gen_distributor(),
        )
        client.post(
            urljoin(repo['_href'], 'actions/publish/'),
            {'id': distributor['id']},
        )
        client.response_handler = api.safe_handler
        url = urljoin('/pulp/repos/', distributor['config']['relative_url'])
        url = urljoin(url, _RPM)
        pulp_rpm = client.get(url).content

        # Does this RPM match the original RPM?
        rpm = client.get(urljoin(_FEED_URL, _RPM)).content
        self.assertEqual(rpm, pulp_rpm)
