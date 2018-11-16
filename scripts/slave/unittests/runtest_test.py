#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for functions in runtest.py."""

import unittest

import mock

import test_env  # pylint: disable=relative-import

from slave import runtest


class FakeLogProcessor(object):
  """A fake log processor to use in the test below."""

  def __init__(self, output):
    self._output = output

  def PerformanceLogs(self):
    return self._output


class GetDataFromLogProcessorTest(unittest.TestCase):
  """Tests related to functions which convert data format."""

  def setUp(self):
    super(GetDataFromLogProcessorTest, self).setUp()

  # Testing private method _GetDataFromLogProcessor.
  # pylint: disable=W0212
  def test_GetDataFromLogProcessor_BasicCase(self):
    """Tests getting of result data from a LogProcessor object."""
    log_processor = FakeLogProcessor({
        'graphs.dat': ['[{"name": "my_graph"}]'],
        'my_graph-summary.dat': ['{"traces": {"x": [1, 0]}, "rev": 123}'],
    })

    # Note that the 'graphs.dat' entry is ignored.
    self.assertEqual(
        {'my_graph': {'traces': {'x': [1, 0]}, 'rev': 123}},
        runtest._GetDataFromLogProcessor(log_processor))

  def test_GetDataFromLogProcessor_OneGraphMultipleLines(self):
    log_processor = FakeLogProcessor({
        'graph-summary.dat': [
            '{"traces": {"x": [1, 0]}, "rev": 123}',
            '{"traces": {"y": [1, 0]}, "rev": 123}',
        ]
    })

    # We always expect the length of the lines list for each graph to be 1.
    # If it doesn't meet this expectation, ignore that graph.
    self.assertEqual({}, runtest._GetDataFromLogProcessor(log_processor))

  def test_GetDataFromLogProcessor_InvalidJson(self):
    log_processor = FakeLogProcessor({
        'graph-summary.dat': ['this string is not valid json']
    })
    self.assertEqual({}, runtest._GetDataFromLogProcessor(log_processor))


class SendResultsToDashboardTest(unittest.TestCase):
  """Tests related to sending requests and saving data from failed requests."""

  def setUp(self):
    super(SendResultsToDashboardTest, self).setUp()

  # Testing private method _GetDataFromLogProcessor.
  # Also, this test method doesn't reference self.
  # pylint: disable=W0212,R0201
  @mock.patch('slave.runtest._GetDataFromLogProcessor')
  @mock.patch('slave.results_dashboard.MakeListOfPoints')
  @mock.patch('slave.results_dashboard.SendResults')
  def test_SendResultsToDashboard_SimpleCase(
      self, SendResults, MakeListOfPoints, GetDataFromLogProcessor):
    """Tests that the right methods get called in _SendResultsToDashboard."""
    # Since this method just tests that certain methods get called when
    # a call to _SendResultsDashboard is made, the data used below is arbitrary.
    fake_charts_data = {'chart': {'traces': {'x': [1, 0]}, 'rev': 1000}}
    fake_points_data = [{'test': 'master/bot/chart/x', 'revision': 1000}]
    fake_results_tracker = mock.Mock()
    fake_results_tracker.IsChartJson = mock.MagicMock(return_value=False)
    fake_results_tracker.IsHistogramSet = mock.MagicMock(return_value=False)
    GetDataFromLogProcessor.return_value = fake_charts_data
    MakeListOfPoints.return_value = fake_points_data

    result = runtest._SendResultsToDashboard(
        fake_results_tracker, {
            'system': 'linux',
            'test': 'sunspider',
            'url': 'http://x.com',
            'build_dir': 'builddir',
            'mastername': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 123,
            'revisions': {'rev': 343},
            'perf_dashboard_machine_group': 'SithLord',
            'supplemental_columns': {}})

    # First a function is called to get data from the log processor.
    GetDataFromLogProcessor.assert_called_with(fake_results_tracker)

    # Then the data is re-formatted to a format that the dashboard accepts.
    MakeListOfPoints.assert_called_with(
        fake_charts_data, 'linux', 'sunspider', 'Builder', 123, {}, 'SithLord')

    # Then a function is called to send the data (and any cached data).
    SendResults.assert_called_with(
        fake_points_data, 'http://x.com', 'builddir', send_as_histograms=False)

    # No errors, should return True.
    self.assertTrue(result)


  @mock.patch('slave.results_dashboard.MakeDashboardJsonV1')
  @mock.patch('slave.results_dashboard.SendResults')
  def test_SendResultsToDashboard_Telemetry(
      self, SendResults, MakeDashboardJsonV1):
    """Tests that the right methods get called in _SendResultsToDashboard."""
    # Since this method just tests that certain methods get called when
    # a call to _SendResultsDashboard is made, the data used below is arbitrary.
    fake_json_data = {
        'chart': {'traces': {'x': [1, 0]}, 'rev': 1000}, 'enabled': True}
    fake_results_tracker = mock.Mock()
    fake_results_tracker.IsChartJson = mock.MagicMock(return_value=True)
    fake_results_tracker.ChartJson = mock.MagicMock(return_value=fake_json_data)
    fake_results_tracker.IsReferenceBuild = mock.MagicMock(return_value=False)
    fake_results_tracker.Cleanup = mock.MagicMock()
    fake_results = {'doesnt': 'matter', 'chart_data': {'enabled': True}}
    MakeDashboardJsonV1.return_value = fake_results

    result = runtest._SendResultsToDashboard(
        fake_results_tracker, {
            'system': 'linux',
            'test': 'sunspider',
            'url': 'http://x.com',
            'build_dir': 'builddir',
            'mastername': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 123,
            'revisions': {'rev': 343},
            'perf_dashboard_machine_group': 'PaiMei',
            'supplemental_columns': {}})

    # Then the data is re-formatted to a format that the dashboard accepts.
    MakeDashboardJsonV1.assert_called_with(
        fake_json_data, {'rev': 343}, 'sunspider', 'linux',
        'Builder', 123, {}, False, 'PaiMei')

    # Then a function is called to send the data (and any cached data).
    SendResults.assert_called_with(
        fake_results, 'http://x.com', 'builddir', send_as_histograms=False)
    fake_results_tracker.Cleanup.assert_called_with()

    # No errors, should return True.
    self.assertTrue(result)


  @mock.patch('slave.results_dashboard.MakeHistogramSetWithDiagnostics')
  @mock.patch('slave.results_dashboard.SendResults')
  @mock.patch('os.getcwd')
  def test_SendResultsToDashboard_Histograms(
      self, getcwd, SendResults, MakeHistogramSetWithDiagnostics):
    """Tests that the right methods get called in _SendResultsToDashboard."""
    # Since this method just tests that certain methods get called when
    # a call to _SendResultsDashboard is made, the data used below is arbitrary.
    fake_results_tracker = mock.Mock()
    fake_results_tracker.IsChartJson = mock.MagicMock(return_value=False)
    fake_results_tracker.IsHistogramSet = mock.MagicMock(return_value=True)
    fake_results_tracker.HistogramFilename = mock.MagicMock(
        return_value='foo.json')
    fake_results_tracker.IsReferenceBuild = mock.MagicMock(return_value=False)
    fake_results_tracker.Cleanup = mock.MagicMock()
    fake_results = {'doesnt': 'matter', 'chart_data': {'enabled': True}}
    MakeHistogramSetWithDiagnostics.return_value = fake_results
    getcwd.return_value = '/some/path/'

    result = runtest._SendResultsToDashboard(
        fake_results_tracker, {
            'system': 'linux',
            'test': 'sunspider',
            'url': 'http://x.com',
            'build_dir': 'builddir',
            'mastername': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 123,
            'revisions': {'rev': 343},
            'perf_dashboard_machine_group': 'PaiMei',
            'supplemental_columns': {}})

    # Then the data is re-formatted to a format that the dashboard accepts.
    MakeHistogramSetWithDiagnostics.assert_called_with(
        histograms_file='foo.json',
        chromium_checkout_path='/some/path/',
        test_name='sunspider',
        bot='linux',
        buildername='Builder',
        buildnumber=123,
        revisions_dict={'--chromium_commit_positions': 343},
        is_reference_build=False,
        perf_dashboard_machine_group='PaiMei')

    # Then a function is called to send the data (and any cached data).
    SendResults.assert_called_with(
        fake_results, 'http://x.com', 'builddir', send_as_histograms=True)
    fake_results_tracker.Cleanup.assert_called_with()

    # No errors, should return True.
    self.assertTrue(result)


  @mock.patch('slave.results_dashboard.MakeDashboardJsonV1')
  @mock.patch('slave.results_dashboard.SendResults')
  def test_SendResultsToDashboard_DisabledBenchmark(
      self, SendResults, MakeDashboardJsonV1):
    """Tests that the right methods get called in _SendResultsToDashboard."""
    # Since this method just tests that certain methods get called when
    # a call to _SendResultsDashboard is made, the data used below is arbitrary.
    fake_json_data = {'chart': {'traces': {'x': [1, 0]}, 'rev': 1000},
        'enabled': True}
    fake_results_tracker = mock.Mock()
    fake_results_tracker.IsChartJson = mock.MagicMock(return_value=True)
    fake_results_tracker.ChartJson = mock.MagicMock(return_value=fake_json_data)
    fake_results_tracker.IsReferenceBuild = mock.MagicMock(return_value=False)
    fake_results_tracker.Cleanup = mock.MagicMock()
    fake_results = {'doesnt': 'matter', 'chart_data': {'enabled': False}}
    MakeDashboardJsonV1.return_value = fake_results

    result = runtest._SendResultsToDashboard(
        fake_results_tracker, {
            'system': 'linux',
            'test': 'sunspider',
            'url': 'http://x.com',
            'build_dir': 'builddir',
            'mastername': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 123,
            'revisions': {'rev': 343},
            'perf_dashboard_machine_group': 'cat',
            'supplemental_columns': {}})

    # Then the data is re-formatted to a format that the dashboard accepts.
    MakeDashboardJsonV1.assert_called_with(
        fake_json_data, {'rev': 343}, 'sunspider', 'linux',
        'Builder', 123, {}, False, 'cat')

    # Make sure SendResults isn't called because the benchmarks is disabled
    self.assertFalse(SendResults.called)

    # No errors, should return True since disabled run is successful.
    self.assertTrue(result)

  @mock.patch('common.chromium_utils.GetActiveMaster')
  @mock.patch('slave.results_dashboard.MakeDashboardJsonV1')
  @mock.patch('slave.results_dashboard.SendResults')
  def test_SendResultsToDashboard_NoTelemetryOutput(
      self, SendResults, MakeDashboardJsonV1, GetActiveMaster):
    """Tests that the right methods get called in _SendResultsToDashboard."""
    fake_results_tracker = mock.Mock()
    fake_results_tracker.IsChartJson = mock.MagicMock(return_value=True)
    fake_results_tracker.ChartJson = mock.MagicMock(return_value=None)
    fake_results_tracker.IsReferenceBuild = mock.MagicMock(return_value=False)
    fake_results_tracker.Cleanup = mock.MagicMock()

    GetActiveMaster.return_value = 'Foo'

    runtest._SendResultsToDashboard(
        fake_results_tracker, {
            'system': 'linux',
            'test': 'sunspider',
            'url': 'http://x.com',
            'build_dir': 'builddir',
            'mastername': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 123,
            'revisions': {'rev': 343},
            'supplemental_columns': {}})

    # Should not call functions to generate JSON and send to JSON if Telemetry
    # did not return results.
    self.assertFalse(MakeDashboardJsonV1.called)
    self.assertFalse(SendResults.called)
    fake_results_tracker.Cleanup.assert_called_with()


  def test_GetPerfDashboardRevisions(self):
    options = mock.MagicMock()
    options.point_id = 1470050195
    options.revision = '294850'
    options.build_properties = {
        'got_webrtc_revision': None,
        'got_v8_revision': 'undefined',
        'git_revision': '9a7b354',
    }
    versions = runtest._GetPerfDashboardRevisions(options)
    self.assertEqual(
        {'rev': '294850', 'git_revision': '9a7b354',
         'point_id': 1470050195},
        versions)


if __name__ == '__main__':
  unittest.main()
