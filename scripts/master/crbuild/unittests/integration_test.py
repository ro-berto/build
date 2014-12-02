#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Crbuild integration unit tests"""

from contextlib import contextmanager
from datetime import datetime
import httplib
import threading
import time
import traceback
import unittest

import test_env  # pylint: disable=W0611

from buildbot.status import builder as build_results
from master.crbuild import integration
from master.unittests.deferred_resource_test import run_deferred
from mock import Mock, call
from twisted.internet import defer, reactor


import apiclient


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

  # Changes
  buildbot.change.number = 5
  buildbot.get_cache.return_value = buildbot.change_cache
  # By default, no cache is in cache.
  buildbot.change_cache.get.return_value = buildbot.change

  # Buildsets
  pending_builds = []
  def add_buildset(*args, **kwargs):
    bsid, brid = len(pending_builds), len(pending_builds)
    pending_build = Mock()
    pending_builds.append(pending_build)

    builder_names = kwargs['builderNames']
    for builder_name in builder_names:
      builder = builders[builder_name]
      builder.pending_builds.append(pending_build)
    return (bsid, brid)
  buildbot.add_buildset.side_effect = add_buildset

  return buildbot


class IntegratorTest(unittest.TestCase):
  namespaces = ['chromium']
  integrator = None
  buildbot = None
  build_service = None
  lease_commit = None
  lease_build_dbg = None
  lease_build_rel = None
  ssid = None

  @contextmanager
  def create_integrator(self, buildbot=None):
    self.build_service = Mock()
    self.buildbot = buildbot or fake_buildbot()
    self.integrator = integration.CrbuildIntegrator(self.namespaces)
    self.integrator.start(self.buildbot, self.build_service)
    try:
      yield
    finally:
      self.integrator.stop()

  def test_no_builds(self):
    with self.create_integrator():
      self.build_service.api.lease.return_value = {
          'commits': [],
          'builds': [],
      }
      run_deferred(self.integrator.poll_builds())
      self.assertTrue(self.build_service.api.lease.called)

  def test_no_leasing_without_available_slaves(self):
    with self.create_integrator():
      self.buildbot.get_available_slaves.return_value = []
      run_deferred(self.integrator.poll_builds())
      self.assertFalse(self.build_service.api.lease.called)

  def test_find_change(self):
    with self.create_integrator():
      m = Mock()
      change = self.integrator._find_change(m.revision, m.commit_key)
      cache = self.integrator.buildbot.change_cache
      cache.get.assert_called_once_with(
          (m.revision, m.commit_key)
      )
      self.assertEqual(change, cache.get.return_value)

  def test_find_change_in_db(self):
    with self.create_integrator():
      change = Mock()
      rev = 123
      commit_key = 'abc'
      change.properties.getProperty.return_value = {'commit_key': commit_key}
      self.buildbot.get_change_by_id.return_value = change
      self.buildbot.find_changes_by_revision.return_value = [change.changeid]

      result = run_deferred(
          self.integrator._find_change_in_db((rev, commit_key))
      )

      self.assertEqual(result, change)
      change.properties.getProperty.assert_any_call(integration.STATE_PROPERTY)
      self.buildbot.find_changes_by_revision.assert_called_once_with(rev)
      self.buildbot.get_change_by_id.assert_called_once_with(change.changeid)

  @contextmanager
  def mock_build_lease(self):
    """Mocks build.lease API call."""
    self.lease_commit = {
        'key': 'commit1',
        'committer': {'email': 'johndoe@chromium.org'},
        'message': 'hello world',
        'revision': 'deadbeef',
        'branch': 'master',
        'createTime': 0,
        'project': 'chromium',
        'repoUrl': 'http://chromium.googlesource.com/chromium/src'
    }
    self.lease_build_rel = {
        'key': 'rel_build',
        'commitKeys': [self.lease_commit['key']],
        'builderName': 'Release'
    }
    self.lease_build_dbg = {
        'key': 'dbg_build',
        'commitKeys': [self.lease_commit['key']],
        'builderName': 'Debug'
    }
    self.build_service.api.lease.return_value = {
        'commits': [self.lease_commit],
        'builds': [self.lease_build_rel, self.lease_build_dbg],
    }
    yield
    self.assertTrue(self.build_service.api.lease.called,
                    'build.lease was not called')

  @contextmanager
  def mock_buildbot_for_one_commit(self, lease_commit):
    """Mocks buildbot.insert_source_stamp_to_db and buildbot.change."""
    self.ssid = 1
    bb = self.buildbot

    # Mock the Change returned by Buildbot.
    change = bb.change
    change.project = lease_commit['project']
    change.branch = lease_commit['branch']
    change.revision = lease_commit['revision']
    change.repository = lease_commit['repoUrl']

    # Mock Buildbot insert source stamp and buildset.
    bb.insert_source_stamp_to_db.return_value = self.ssid

    yield

    # Assert requested the change from buidlbot change cache.
    bb.change_cache.get.assert_called_once_with(
        (change.revision, lease_commit['key'])
    )

    # Assert inserted a source stamp for the change.
    bb.insert_source_stamp_to_db.assert_called_once_with(
        branch=change.branch,
        revision=change.revision,
        repository=change.repository,
        project=change.project,
        changeids=[change.number]
    )

  def assert_added_buildset(self, lease_build, ssid):
    self.integrator.buildbot.add_buildset.assert_any_call(
        ssid=ssid,
        reason=integration.CHANGE_REASON,
        builderNames=[lease_build['builderName']],
        properties={
            'crbuild': ({'build_key': lease_build['key']}, 'crbuild'),
        },
        external_idstring=lease_build['key'],
    )

  def assert_build_was_unleased(self, build_key):
    self.build_service.api.update.assert_any_call(body={
        'buildKey': build_key,
        'leaseSeconds': 0, # Unlease.
    })

  def test_all_scheduled(self):
    with self.create_integrator():
      bb = self.buildbot

      with self.mock_build_lease():
        with self.mock_buildbot_for_one_commit(self.lease_commit):
          run_deferred(self.integrator.poll_builds())

      # Assert added two buildsets. No builds were left unscheduled.
      self.assertEqual(bb.add_buildset.call_count, 2)
      self.assert_added_buildset(self.lease_build_rel, self.ssid)
      self.assert_added_buildset(self.lease_build_dbg, self.ssid)

      # Assert did not unlease builds because all builds where scheduled.
      # TODO(nodir): check that there were no checks with leaseSeconds=0
      self.assertEqual(0, self.build_service.api.update.call_count)

  def test_one_slave_for_two_builders(self):
    bb = fake_buildbot(one_slave=True)
    with self.create_integrator(bb):
      with self.mock_build_lease():
        with self.mock_buildbot_for_one_commit(self.lease_commit):
          run_deferred(self.integrator.poll_builds())
      # Assert added two buildsets. No builds were left unscheduled.
      self.assertEqual(bb.add_buildset.call_count, 1)

  def test_build_not_scheduled_if_builder_name_is_wrong(self):
    with self.create_integrator():
      bb = self.integrator.buildbot
      bb.add_buildset.return_value = (1, 1)

      # No Debug builder.
      del bb.get_builders.return_value['Debug']

      with self.mock_build_lease():
        with self.mock_buildbot_for_one_commit(self.lease_commit):
          run_deferred(self.integrator.poll_builds())

      # Assert added one buildset of two.
      self.assertEqual(bb.add_buildset.call_count, 1)
      self.assert_build_was_unleased(self.lease_build_dbg['key'])

  def test_nothing_is_scheduled_if_builders_do_not_have_available_slaves(self):
    with self.create_integrator():
      bb = self.integrator.buildbot

      # Add one more slave, not assigned to builders,
      # and make others unavailable.
      available_slave = Mock()
      bb.getSlaves.return_value.append(available_slave)
      bb.is_slave_available.side_effect = lambda s: s == available_slave

      with self.mock_build_lease():
        run_deferred(self.integrator.poll_builds())

      self.assertFalse(bb.add_buildset.called, 'A build was scheduled')
      self.assert_build_was_unleased(self.lease_build_rel['key'])
      self.assert_build_was_unleased(self.lease_build_dbg['key'])

  def test_nothing_is_scheduled_if_builders_have_many_pending_builds(self):
    with self.create_integrator():
      bb = self.integrator.buildbot

      # Add some pending builds to each builder.
      for builder in bb.get_builders.return_value.itervalues():
        many_mocks_func = lambda: [Mock() for _ in range(100)]
        builder.getPendingBuildRequestStatuses.side_effect = many_mocks_func

      with self.mock_build_lease():
        run_deferred(self.integrator.poll_builds())

      self.assertFalse(bb.add_buildset.called, 'A build was scheduled')
      self.assert_build_was_unleased(self.lease_build_rel['key'])
      self.assert_build_was_unleased(self.lease_build_dbg['key'])

  @contextmanager
  def mock_existing_build(self):
    build = Mock()
    build.key = 'buildKey'
    build.properties.getProperty.return_value = {
       'build_key': build.key,
    }

    yield build

    build.properties.getProperty.assert_any_call(integration.STATE_PROPERTY)

  def test_build_started(self):
    with self.create_integrator(), self.mock_existing_build() as build:
      self.integrator.on_build_started(build)

      # Extract update's body arg.
      update = self.build_service.api.update
      self.assertEqual(1, update.call_count)
      _, kwargs = update.call_args
      body = kwargs['body']

      self.assertEqual(body['buildKey'], build.key)
      self.assertTrue(body['leaseSeconds'] > 10)
      self.assertEqual(body['url'], self.buildbot.get_build_url.return_value)
      self.assertEqual(body['status'], 'BUILDING')

  def test_build_succeeded(self):
    with self.create_integrator(), self.mock_existing_build() as build:
      self.integrator.on_build_finished(build, 'SUCCESS')
      self.build_service.api.update.assert_called_once_with(body={
          'buildKey': build.key,
          'status': 'SUCCESS',
          'leaseSeconds': 0,
      })

  def test_build_failed(self):
    with self.create_integrator(), self.mock_existing_build() as build:
      self.integrator.on_build_finished(build, 'FAILURE')
      self.build_service.api.update.assert_called_once_with(body={
          'buildKey': build.key,
          'status': 'FAILURE',
          'leaseSeconds': 0,
      })


if __name__ == '__main__':
  unittest.main()
