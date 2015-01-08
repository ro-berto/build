#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbucket integration unit tests"""

import contextlib
import datetime
import httplib
import json
import logging
import sys
import threading
import time
import traceback
import unittest

import test_env  # pylint: disable=W0611

from buildbot.status import builder as build_results
from master.buildbucket import common, integration
from master.unittests.deferred_resource_test import run_deferred
from mock import Mock, call
from twisted.internet import defer, reactor
import apiclient


LEASE_KEY = 42


def fake_buildbot(one_slave=False):
  buildbot = Mock()

  # Slaves
  buildbot.get_slaves.return_value = [buildbot.slave]
  if not one_slave:
    buildbot.get_slaves.return_value.append(buildbot.slave2)
  buildbot.get_available_slaves.return_value = buildbot.get_slaves.return_value
  buildbot.is_slave_available.return_value = True

  # Builders
  def mock_builder():
    builder = Mock()
    builder.getSlaves.return_value = buildbot.get_slaves.return_value
    builder.pending_builds = []
    get_pending = builder.getPendingBuildRequestStatuses
    get_pending.return_value = builder.pending_builds
    return builder

  builders = {
      'Debug': mock_builder(),
      'Release': mock_builder(),
  }
  buildbot.get_builders.return_value = builders

  # Buildsets
  pending_builds = []
  def add_buildset(*args, **kwargs):
    bsid, brid = len(pending_builds), len(pending_builds)
    builder_names = kwargs['builderNames']
    for builder_name in builder_names:
      pending_build = Mock()
      pending_builds.append(pending_build)
      builder = builders[builder_name]
      builder.pending_builds.append(pending_build)
    return (bsid, brid)
  buildbot.add_buildset.side_effect = add_buildset

  return buildbot


def fake_buildbucket():
  service = Mock()
  def lease(id, body):  # pylint: disable=W0622
    return {
        'build': {
            'lease_key': LEASE_KEY,
            'lease_expiration_ts': body['lease_expiration_ts'],
        }
    }
  service.api.lease.side_effect = lease

  return service


class IntegratorTest(unittest.TestCase):
  ssid = 1
  buckets = ['chromium']
  integrator = None
  buildbot = None
  buildbucket = None
  buildbucket_change = {
      'id': '1',
      'committer': {'email': 'johndoe@chromium.org'},
      'message': 'hello world',
      'revision': 'deadbeef',
      'branch': 'master',
      'create_ts': 1419984000000000,  # 2014-11-31
      'project': 'chromium',
      'repoUrl': 'http://chromium.googlesource.com/chromium/src'
  }
  buildbucket_build_rel = {
      'id': '1',
      'parameters_json': json.dumps({
            'builder_name': 'Release',
            'changes': [buildbucket_change],
      }),
  }
  buildbucket_build_dbg = {
      'id': '2',
      'parameters_json': json.dumps({
            'builder_name': 'Debug',
            'changes': [buildbucket_change],
      }),
  }

  def setUp(self):
    super(IntegratorTest, self).setUp()
    self.changes = Mock()
    self.changes.get_source_stamp.return_value = self.ssid

  @contextlib.contextmanager
  def create_integrator(self, buildbot=None):
    self.buildbucket = fake_buildbucket()
    self.buildbot = buildbot or fake_buildbot()
    self.integrator = integration.BuildBucketIntegrator(self.buckets)
    def log(msg, level=logging.INFO):
      logging.log(level, msg)
    self.integrator.log = log
    self.integrator.start(
        self.buildbot, self.buildbucket,
        change_store_factory=lambda bb: self.changes)
    try:
      yield
    finally:
      self.integrator.stop()

  def test_no_builds(self):
    with self.create_integrator():
      self.buildbucket.api.peek.return_value = {'builds': []}
      run_deferred(self.integrator.poll_builds())
      self.assertFalse(self.buildbot.add_buildset.called)
      self.assertTrue(self.buildbucket.api.peek.called)
      self.assertFalse(self.buildbucket.api.lease.called)

  def test_no_leasing_without_available_slaves(self):
    with self.create_integrator():
      self.buildbot.get_available_slaves.return_value = []
      run_deferred(self.integrator.poll_builds())
      self.assertFalse(self.buildbucket.api.peek.called)

  def test_error_in_peek_response(self):
    with self.create_integrator():
      self.buildbucket.api.peek.return_value = {
          'error': {
              'reason': 'PROBLEM',
              'message': 'Something is bad',
          }
      }
      run_deferred(self.integrator.poll_builds())
      self.assertFalse(self.buildbucket.api.lease.called)

  def test_build_was_not_leased(self):
    with self.create_integrator(), self.mock_build_peek():
      self.buildbucket.api.lease.return_value = {
          'error': {
              'reason': 'CANNOT_LEASE_BUILD',
              'message': 'Sorry',
          }
      }
      self.buildbucket.api.lease.side_effect = None
      run_deferred(self.integrator.poll_builds())
      self.assertFalse(self.buildbot.add_buildset.called)

  @contextlib.contextmanager
  def mock_build_peek(self, lease=True):
    """Mocks buildbucket.peek API call."""
    self.buildbucket.api.peek.return_value = {
        'builds': [self.buildbucket_build_rel, self.buildbucket_build_dbg],
    }
    yield
    self.assertTrue(
        self.buildbucket.api.peek.called, 'build.peek was not called')

  def assert_added_buildset(
      self, build_id, builder_name, ssid, properties=None):
    expected_build_info = {
        'build_id': build_id,
        'lease_key': LEASE_KEY,
    }
    properties = (properties or {}).copy()
    properties['buildbucket'] =  expected_build_info
    properties = {
        k: (v, 'buildbucket') for k, v in properties.iteritems()
    }

    self.integrator.buildbot.add_buildset.assert_any_call(
        ssid=ssid,
        reason=common.CHANGE_REASON,
        builderNames=[builder_name],
        properties=properties,
        external_idstring=build_id,
    )

  def assert_leased(self, build_id):
    ten_second_from_now = common.datetime_to_timestamp(
        datetime.datetime.utcnow() + datetime.timedelta(seconds=10))

    for _, kwargs in self.buildbucket.api.lease.call_args_list:
      body = kwargs['body']
      if kwargs['id'] == build_id:
        self.assertGreaterEqual(
            body['lease_expiration_ts'], ten_second_from_now)
        return
    self.fail('Build %s was not leased' % build_id)

  def test_minimalistic_build(self):
    with self.create_integrator():
      self.buildbucket.api.peek.return_value = {
          'builds': [{
              'id': '1',
              'parameters_json': json.dumps({
                    'builder_name': 'Release',
              }),
          }],
      }

      run_deferred(self.integrator.poll_builds())

      self.assert_leased('1')
      self.assert_added_buildset('1', 'Release', self.ssid)

  def test_build_with_properties(self):
    with self.create_integrator():
      self.buildbucket.api.peek.return_value = {
          'builds': [{
              'id': '1',
              'parameters_json': json.dumps({
                    'builder_name': 'Release',
                    'properties': {
                        'a': 'b',
                    }
              }),
          }],
      }

      run_deferred(self.integrator.poll_builds())

      self.assert_leased('1')
      self.assert_added_buildset(
          '1', 'Release', self.ssid, properties={'a': 'b'})

  def test_all_scheduled(self):
    with self.create_integrator():
      with self.mock_build_peek():
        run_deferred(self.integrator.poll_builds())

      self.assert_leased(self.buildbucket_build_rel['id'])
      self.assert_leased(self.buildbucket_build_dbg['id'])

      # Assert added two buildsets
      self.assertEqual(self.buildbot.add_buildset.call_count, 2)
      self.assert_added_buildset(
          self.buildbucket_build_rel['id'], 'Release', self.ssid)
      self.assert_added_buildset(
          self.buildbucket_build_dbg['id'], 'Debug', self.ssid)

  def test_polling_with_cursor(self):
    with self.create_integrator():
      peek_response1 = {
          'builds': [self.buildbucket_build_rel],
          'next_cursor': '123',

      }
      peek_response2 = {
          'builds': [self.buildbucket_build_dbg],
      }
      self.buildbucket.api.peek.side_effect = [peek_response1, peek_response2]

      run_deferred(self.integrator.poll_builds())

      self.assertEqual(self.buildbucket.api.peek.call_count, 2)
      _, last_peek_call_kwargs = self.buildbucket.api.peek.call_args
      self.assertEqual(
          last_peek_call_kwargs['start_cursor'],
          peek_response1['next_cursor'])

      self.assert_leased(self.buildbucket_build_rel['id'])
      self.assert_leased(self.buildbucket_build_dbg['id'])

      # Assert added two buildsets
      self.assertEqual(self.buildbot.add_buildset.call_count, 2)
      self.assert_added_buildset(
          self.buildbucket_build_rel['id'], 'Release', self.ssid)
      self.assert_added_buildset(
          self.buildbucket_build_dbg['id'], 'Debug', self.ssid)

  def test_one_slave_for_two_builders(self):
    bb = fake_buildbot(one_slave=True)
    with self.create_integrator(bb):
      with self.mock_build_peek():
        run_deferred(self.integrator.poll_builds())
      # Assert only on build was leased and scheduled
      self.assertEqual(bb.add_buildset.call_count, 1)
      self.assertEqual(self.buildbucket.api.lease.call_count, 1)

  def test_build_not_scheduled_if_builder_name_is_wrong(self):
    with self.create_integrator():
      bb = self.integrator.buildbot
      bb.add_buildset.return_value = (1, 1)

      # No Debug builder.
      del bb.get_builders.return_value['Debug']

      with self.mock_build_peek():
        run_deferred(self.integrator.poll_builds())

      # Assert added one buildset of two.
      self.assertEqual(self.buildbucket.api.lease.call_count, 1)
      self.assertEqual(bb.add_buildset.call_count, 1)

  def test_nothing_is_scheduled_if_builders_do_not_have_available_slaves(self):
    with self.create_integrator():
      bb = self.integrator.buildbot

      # Add one more slave, not assigned to builders,
      # and make others unavailable.
      available_slave = Mock()
      bb.getSlaves.return_value.append(available_slave)
      bb.is_slave_available.side_effect = lambda s: s == available_slave

      with self.mock_build_peek():
        run_deferred(self.integrator.poll_builds())

      self.assertFalse(bb.add_buildset.called, 'A build was scheduled')

  def test_nothing_is_scheduled_if_builders_have_many_pending_builds(self):
    with self.create_integrator():
      bb = self.integrator.buildbot

      # Add some pending builds to each builder.
      for builder in bb.get_builders.return_value.itervalues():
        many_builds = [Mock() for _ in range(100)]
        builder.getPendingBuildRequestStatuses.side_effect = lambda: many_builds

      with self.mock_build_peek():
        run_deferred(self.integrator.poll_builds())

      self.assertFalse(self.buildbucket.api.lease.called, 'A build was leased')
      self.assertFalse(bb.add_buildset.called, 'A build was scheduled')

  @contextlib.contextmanager
  def mock_existing_build(self):
    build = Mock()
    build.id = '123321'
    info = {
       'build_id': build.id,
       'lease_key': LEASE_KEY,
    }
    build.properties.getProperty.return_value = info
    properties = {
        'a': 'b',
    }
    as_dict_result = properties.copy()
    as_dict_result[common.INFO_PROPERTY] = info
    build.getProperties.return_value.asDict.return_value = as_dict_result
    build.expected_result_details_json = json.dumps(
        {'properties': properties}, sort_keys=True)

    yield build

    build.properties.getProperty.assert_any_call(common.INFO_PROPERTY)

  def test_build_started(self):
    with self.create_integrator(), self.mock_existing_build() as build:
      self.buildbucket.api.start.return_value = {}
      self.integrator.on_build_started(build)

      self.buildbucket.api.start.assert_called_once_with(
          id=build.id,
          body={
              'lease_key': LEASE_KEY,
              'url': self.buildbot.get_build_url.return_value,
          })

  def test_build_started_error_response(self):
    with self.create_integrator(), self.mock_existing_build() as build:
      self.buildbucket.api.start.return_value = {
          'error': {
              'reason': 'BAD',
              'message': 'Something is bad',
          },
      }
      self.integrator.on_build_started(build)

  def test_build_succeeded(self):
    with self.create_integrator(), self.mock_existing_build() as build:
      self.buildbucket.api.succeed.return_value = {}

      self.integrator.on_build_finished(build, 'SUCCESS')

      self.buildbucket.api.succeed.assert_called_once_with(
          id=build.id,
          body={
              'lease_key': LEASE_KEY,
              'result_details_json': build.expected_result_details_json,
          }
      )

  def test_build_failed(self):
    with self.create_integrator(), self.mock_existing_build() as build:
      self.buildbucket.api.fail.return_value = {}

      self.integrator.on_build_finished(build, 'FAILURE')

      self.buildbucket.api.fail.assert_called_once_with(
          id=build.id,
          body={
              'lease_key': LEASE_KEY,
              'failure_reason': 'BUILD_FAILURE',
              'result_details_json': build.expected_result_details_json,
          }
      )


if __name__ == '__main__':
  logging.basicConfig(
      level=(logging.DEBUG if '-v' in sys.argv else logging.FATAL))
  if '-v' in sys.argv:
    unittest.TestCase.maxDiff = None
  unittest.main()
