#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for log processor testcases.

These tests should be run from the directory in which the script lives, so it
can find its data/ directory.

"""

import filecmp
import mock
import os
import shutil
import stat
import unittest

import simplejson

from master import chromium_step
from common import chromium_utils
from master.log_parser import process_log

import runtests


class GoogleLoggingStepTest(unittest.TestCase):
  """ Logging testcases superclass

  The class provides some operations common for testcases.
  """
  def setUp(self):
    self._RemoveOutputDir()
    self._revision = 12345
    self._report_link = 'http://localhost/~user/report.html'
    self._output_dir = 'output_dir'

  def tearDown(self):
    if os.path.exists(self._output_dir):
      directoryListing = os.listdir(self._output_dir)
      for filename in directoryListing:
        file_stats = os.stat(os.path.join(self._output_dir, filename))
        self._assertReadable(file_stats)
    self._RemoveOutputDir()

  def _assertReadable(self, file_stats):
    mode = file_stats[stat.ST_MODE]
    self.assertEqual(4, mode & stat.S_IROTH)

  def _ConstructStep(self, log_processor_class, logfile,
                     factory_properties=None, perf_expectations_path=None):
    """ Common approach to construct chromium_step.ProcessLogTestStep
    type instance with LogFile instance set.
    Args:
      log_processor_class: type/class of type chromium_step.ProcessLogTestStep
        that is going to be constructed. E.g. PagecyclerTestStep
      logfile: filename with setup process log output.
    """
    factory_properties = factory_properties or {}
    self._log_processor_class = chromium_utils.InitializePartiallyWithArguments(
        log_processor_class, factory_properties=factory_properties,
        report_link=self._report_link, output_dir=self._output_dir,
        perf_name='test-system', test_name='test-name',
        perf_filename=perf_expectations_path)
    step = self._CreateStep(self._log_processor_class)
    log_file = self._LogFile(
        'stdio', open(os.path.join(runtests.DATA_PATH, logfile)).read())
    self._SetupBuild(step, self._revision, log_file)
    return step

  def _CreateStep(self, log_processor_class):
    """ Creates the appropriate step for this test case. This is in its
    own function so it can be overridden by subclasses as needed.
    Args:
      log_processor_class: type/class of type chromium_step.ProcessLogTestStep
        that is going to be constructed. E.g. PagecyclerTestStep
    """
    return chromium_step.ProcessLogShellStep(log_processor_class)

  def _SetupBuild(self, step, revision, log_file):
    class BuildMock(mock.Mock):
      def __init__(self, revision, log_files):
        mock.Mock.__init__(self)
        self._revision = revision
        self._getLogsCalled = 0
        self._log_files = log_files

      def getProperty(self, property_name):
        mock.Mock.__getattr__(self, 'getProperty')
        if property_name == 'got_revision':
          return self._revision
        return None

      def getLogs(self):
        mock.Mock.__getattr__(self, 'getLogs')
        self._getLogsCalled += 1
        if self._getLogsCalled > 1:
          raise Exception('getLogs called more than once')
        return self._log_files

    build_mock = BuildMock(revision, [log_file])
    step.step_status = build_mock
    step.build = build_mock

  def _LogFile(self, name, content):
    class LogMock(mock.Mock):
      def __init__(self, name, content):
        mock.Mock.__init__(self)
        self._name = name
        self._content = content

      def getName(self):
        return self._name

      def getText(self):
        return self._content

    log_file_mock = LogMock(name, content)
    return log_file_mock

  def _JoinWithSpaces(self, array):
    return ' '.join([str(x) for x in array])

  def _JoinWithSpacesAndNewLine(self, array):
    return '%s\n' % self._JoinWithSpaces(array)

  def _RemoveOutputDir(self):
    if os.path.exists('output_dir'):
      shutil.rmtree('output_dir')


class BenchpressPerformanceTestStepTest(GoogleLoggingStepTest):

  def testPrependsSummaryBenchpress(self):
    files_that_are_prepended = ['summary.dat']
    os.mkdir('output_dir')
    for filename in files_that_are_prepended:
      filename = os.path.join('output_dir', filename)
      file = open(filename, 'w')
      control_line = 'this is a line one, should become line two'
      file.write(control_line)
      file.close()
      step = self._ConstructStep(process_log.BenchpressLogProcessor,
                                'benchpress_log')
      step.commandComplete('mycommand')

      self.assert_(os.path.exists(filename))
      text = open(filename).read()
      self.assert_(len(text.splitlines()) > 1,
                   'File %s was not prepended' % filename)
      self.assertEqual(control_line, text.splitlines()[1],
                       'File %s was not prepended' % filename)

  def testBenchpressSummary(self):
    step = self._ConstructStep(process_log.BenchpressLogProcessor,
                               'benchpress_log')
    step.commandComplete('mycommand')

    self.assert_(os.path.exists('output_dir/summary.dat'))
    actual = open('output_dir/summary.dat').readline()
    expected = '12345 469 165 1306 64 676 38 372 120 232 294 659 1157 397\n'
    self.assertEqual(expected, actual)

  def testCreateReportLink(self):
    class StepMock(mock.Mock):
      def __init__(self, urltype, reportlink):
        mock.Mock.__init__(self)
        self._urltype = urltype
        self._reportlink = reportlink
        self._addURLCalled = 0

      def addURL(self, urltype, link):
        mock.Mock.__getattr__(self, 'addURL')
        self._addURLCalled += 1
        if self._addURLCalled > 1:
          raise Exception('getLogs called more than once')
        if urltype != self._urltype:
          raise Exception('url_type should be \'%s\'' % self._urltype)
        if link != self._reportlink:
          raise Exception('link should have been \'%s\'' % self._reportlink)

    log_processor_class = chromium_utils.InitializePartiallyWithArguments(
        process_log.BenchpressLogProcessor, report_link=self._report_link,
        output_dir=self._output_dir)
    step = chromium_step.ProcessLogShellStep(log_processor_class)
    build_mock = mock.Mock()
    source_mock = mock.Mock()
    change_mock = mock.Mock()
    change_mock.revision = self._revision
    source_mock.changes = [change_mock]
    build_mock.source = source_mock
    step_status = StepMock('results', log_processor_class().ReportLink())
    step.build = build_mock
    step.step_status = step_status
    step._CreateReportLinkIfNeccessary()
    build_mock.verify()


class PlaybackLogProcessorTest(GoogleLoggingStepTest):
  def testDetails(self):
    step = self._ConstructStep(process_log.PlaybackLogProcessor,
                              'playback_log')

    step.commandComplete('mycommand')
    expected = simplejson.dumps(
      {'12345':
        {
          'reference':
          {
            't:V8.ParseLazy':
            {
              'data': [210, 240, 225]
            },
            'c:V8.TotalExternalStringMemory':
            {
              'data': [3847860, 3845000, 3849000]
            }
          },
          'latest':
          {
            't:V8.ParseLazy':
            {
              'data': [200, 190, 198]
            },
            'c:V8.TotalExternalStringMemory':
            {
              'data': [3847850, 3846900, 3848450]
            }
          }
        }
      }
    )

    self.assert_(os.path.exists('output_dir/details.dat'))

    actual = open('output_dir/details.dat').readline()
    self.assertEqual(expected + '\n', actual)

  def testSummary(self):
    step = self._ConstructStep(process_log.PlaybackLogProcessor,
                              'playback_log')

    step.commandComplete('mycommand')
    expected = simplejson.dumps(
      {'12345':
        {
          'reference':
          {
            't:V8.ParseLazy':
            {
              'mean': '225.00',
              'stdd': '12.25'
            },
            'c:V8.TotalExternalStringMemory':
            {
              'mean': '3847286.67',
              'stdd': '1682.56'
            }
          },
          'latest':
          {
            't:V8.ParseLazy':
            {
              'mean': '196.00',
              'stdd': '4.32'
            },
            'c:V8.TotalExternalStringMemory':
            {
              'mean': '3847733.33',
              'stdd': '638.14'
            }
          }
        }
      }
    )

    self.assert_(os.path.exists('output_dir/summary.dat'))

    actual = open('output_dir/summary.dat').readline()
    self.assertEqual(expected + '\n', actual)


class GraphingLogProcessorTest(GoogleLoggingStepTest):

  def _TestPerfExpectations(self, perf_expectations_file):
    perf_expectations_path = os.path.join(
        runtests.DATA_PATH, perf_expectations_file)
    step = self._ConstructStep(process_log.GraphingLogProcessor,
                               'graphing_processor.log',
                               factory_properties={'expectations': True,
                                                   'perf_id': 'tester'},
                               perf_expectations_path=perf_expectations_path)
    step.commandComplete('mycommand')
    actual_file = os.path.join('output_dir', 'graphs.dat')
    self.assert_(os.path.exists(actual_file))
    actual = simplejson.load(open(actual_file))
    expected = simplejson.load(open(
        os.path.join(runtests.DATA_PATH, 'graphing_processor-graphs.dat')))
    self.assertEqual(expected, actual)
    return step

  def testSummary(self):
    step = self._ConstructStep(process_log.GraphingLogProcessor,
                               'graphing_processor.log')
    step.commandComplete('mycommand')
    for graph in ('commit_charge', 'ws_final_total', 'vm_final_browser',
                  'vm_final_total', 'ws_final_browser', 'processes',
                  'artificial_graph'):
      filename = '%s-summary.dat' % graph
      self.assert_(os.path.exists(os.path.join('output_dir', filename)))
      # Since the output files are JSON-encoded, they may differ in form, but
      # represent the same data. Therefore, we decode them before comparing.
      actual = simplejson.load(open(os.path.join('output_dir', filename)))
      expected = simplejson.load(open(os.path.join(runtests.DATA_PATH,
                                                   filename)))
      self.assertEqual(expected, actual)

  def testFrameRateSummary(self):
    step = self._ConstructStep(process_log.GraphingFrameRateLogProcessor,
                               'frame_rate_graphing_processor.log')
    step.commandComplete('mycommand')
    for graph in ('blank', 'googleblog'):
      filename = '%s-summary.dat' % graph
      self.assert_(os.path.exists(os.path.join('output_dir', filename)))
      # Since the output files are JSON-encoded, they may differ in form, but
      # represent the same data. Therefore, we decode them before comparing.
      actual = simplejson.load(open(os.path.join('output_dir', filename)))
      expected = simplejson.load(
          open(os.path.join(runtests.DATA_PATH, 'frame_rate', filename)))
      self.assertEqual(expected, actual)

  def testFrameRateGestureList(self):
    step = self._ConstructStep(process_log.GraphingFrameRateLogProcessor,
                               'frame_rate_graphing_processor.log')
    step.commandComplete('mycommand')
    for graph in ('blank', 'googleblog'):
      for trace in ('fps', 'fps_ref'):
        filename = "%s_%s_%s.dat" % (self._revision, graph, trace)
        self.assert_(os.path.exists(os.path.join('output_dir', filename)))
        actual = os.path.join('output_dir', filename)
        expected = os.path.join(runtests.DATA_PATH, 'frame_rate', filename)
        self.assert_(filecmp.cmp(actual, expected))

  def testGraphList(self):
    step = self._ConstructStep(process_log.GraphingLogProcessor,
                               'graphing_processor.log')
    step.commandComplete('mycommand')
    actual_file = os.path.join('output_dir', 'graphs.dat')
    self.assert_(os.path.exists(actual_file))
    actual = simplejson.load(open(actual_file))
    expected = simplejson.load(open(
        os.path.join(runtests.DATA_PATH, 'graphing_processor-graphs.dat')))
    self.assertEqual(expected, actual)

  def testPerfExpectationsImproveRelative(self):
    step = self._TestPerfExpectations('perf_improve_relative.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (25.00%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressRelative(self):
    step = self._TestPerfExpectations('perf_regress_relative.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (50.00%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressAbsolute(self):
    step = self._TestPerfExpectations('perf_regress_absolute.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (2.49%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveAbsolute(self):
    step = self._TestPerfExpectations('perf_improve_absolute.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (3.20%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeRelative(self):
    step = self._TestPerfExpectations('perf_nochange_relative.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeAbsolute(self):
    step = self._TestPerfExpectations('perf_nochange_absolute.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerSuccess(self):
    step = self._TestPerfExpectations('perf_test_better_lower_success.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerImprove(self):
    step = self._TestPerfExpectations('perf_test_better_lower_improve.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerRegress(self):
    step = self._TestPerfExpectations('perf_test_better_lower_regress.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherSuccess(self):
    step = self._TestPerfExpectations('perf_test_better_higher_success.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherImprove(self):
    step = self._TestPerfExpectations('perf_test_better_higher_improve.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherRegress(self):
    step = self._TestPerfExpectations('perf_test_better_higher_regress.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))


if __name__ == '__main__':
  unittest.main()
