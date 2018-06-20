#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""DeferredResource unit tests"""

import httplib
import unittest

from contextlib import contextmanager

import httplib2

from mock import NonCallableMock, Mock, call

import test_env  # pylint: disable=relative-import

from master.deferred_resource import DeferredResource
from twisted.internet import reactor
from twisted.python.threadpool import ThreadPool

import apiclient

from infra_libs import ts_mon


def run_deferred(deferred, timeout=1, print_traceback=True):
  failures = []
  results = []
  def stop_reactor():
    if reactor.running:
      # Stop immediately.
      reactor.crash()
  def on_success(result):
    stop_reactor()
    results.append(result)

  def on_failure(failure):
    stop_reactor()
    failures.append(failure)

  deferred.addCallback(on_success)
  deferred.addErrback(on_failure)

  if not deferred.called:
    reactor.callLater(timeout, stop_reactor)
    assert not reactor.running
    reactor.run()
    assert not reactor.running

  assert (len(results) == 1) != (len(failures) == 1)

  if failures:
    assert len(failures) == 1, 'More than one failure'
    fail = failures[0]
    if print_traceback:
      fail.printTraceback()
    fail.raiseException()
  return results[0]


def fake_resource():
  resource = NonCallableMock()
  resource.greet.__name__ = 'greet'
  return resource


class DeferredResourceTest(unittest.TestCase):
  resource = None
  deferred_resource = None

  def setUp(self):
    super(DeferredResourceTest, self).setUp()

  @contextmanager
  def create_resource(self, credentials=None):
    self.resource = fake_resource()
    self.deferred_resource = DeferredResource(
        resource=self.resource,
        credentials=credentials,
        retry_wait_seconds=0.1, # Run tests fast.
        http_client_name='unittest',
    )
    with self.deferred_resource:
      yield

  class BadFactoryError(Exception):
    pass

  def bad_factory(self):
    raise self.BadFactoryError()

  def test_method_is_called(self):
    with self.create_resource():
      result = run_deferred(
          self.deferred_resource.api.greet(1, 2, a=3)
      )
      self.resource.greet.assert_called_once_with(1, 2, a=3)
      self.assertEqual(
          result,
          self.resource.greet.return_value.execute.return_value,
      )

  def test_transient_errors_are_retried(self):
    with self.create_resource():
      execute = self.resource.greet.return_value.execute

      # Mock a transient error in greet().execute()
      transient_error_count = 2
      def transient_error(*args, **kwargs):
        if transient_error.raised_count < transient_error_count:
          transient_error.raised_count += 1
          resp = Mock(status=httplib.INTERNAL_SERVER_ERROR)
          raise apiclient.errors.HttpError(resp, '')
        return execute.return_value
      transient_error.raised_count = 0
      execute.side_effect = transient_error

      actual = run_deferred(self.deferred_resource.api.greet())
      self.assertEqual(execute.call_count, transient_error_count + 1)
      self.assertEqual(execute.return_value, actual)

  def test_bad_request(self):
    with self.create_resource():
      # Mock a BAD_REQUEST response.
      def bad_request_error(*args, **kwargs):
        resp = Mock(status=httplib.BAD_REQUEST)
        raise apiclient.errors.HttpError(resp, '')
      self.resource.greet.return_value.execute.side_effect = bad_request_error

      with self.assertRaises(apiclient.errors.HttpError):
        run_deferred(
            self.deferred_resource.api.greet(),
            print_traceback=False
        )

  def test_async_create(self):
    res = fake_resource()
    def_res = run_deferred(
        DeferredResource._create_async(lambda: res, http_client_name='unittest')
    )
    try:
      self.assertTrue(isinstance(def_res, DeferredResource))
      self.assertEqual(def_res._resource, res)
    finally:
      def_res.stop()

  def test_async_create_with_bad_request_factory(self):
    pool = DeferredResource._create_thread_pool(1, 'unittest')
    try:
      with self.assertRaises(self.BadFactoryError):
        run_deferred(
            DeferredResource._create_async(
                self.bad_factory, _pool=pool, http_client_name='unittest'),
            print_traceback=False
        )
      self.assertFalse(pool.threads)
    finally:
      pool.stop()


class ThreadPoolTest(unittest.TestCase):
  """Test for the monitoring code we added to twistd's ThreadPool."""

  def setUp(self):
    ts_mon.reset_for_unittest()
    ThreadPool._runningThreadPools = []

  def test_start_stop(self):
    tp = ThreadPool(name='foo')
    self.assertEqual([], ThreadPool._runningThreadPools)
    tp.start()
    self.assertEqual([tp], ThreadPool._runningThreadPools)
    tp.stop()
    self.assertEqual([], ThreadPool._runningThreadPools)

  @unittest.skip("flaky")
  def test_working_metric(self):
    tp = ThreadPool(name='foo', minthreads=1)
    tp.start()
    tp.callInThread(ThreadPool._setGlobalMetrics)
    tp.stop()

    fields = {'name': 'foo'}
    self.assertEqual(1, ThreadPool._queueMetric.get(fields))
    self.assertEqual(0, ThreadPool._waitingMetric.get(fields))
    self.assertEqual(1, ThreadPool._workingMetric.get(fields))

  def test_no_name_no_metrics(self):
    tp = ThreadPool(minthreads=1)
    tp.start()
    tp.callInThread(ThreadPool._setGlobalMetrics)
    tp.stop()

    fields = {'name': ''}
    self.assertEqual(None, ThreadPool._queueMetric.get(fields))


if __name__ == '__main__':
  unittest.main()
