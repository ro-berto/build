#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for annotated log parsers in runtest.py.

runtest.py has the option to parse test output locally and send results to the
master via annotator steps. This file tests those parsers.

"""

import json
import os
import unittest

import test_env  # pylint: disable=W0403,W0611

from slave import process_log_utils

TEST_PERCENTILES = [.05, .3, .8]

class LoggingStepBase(unittest.TestCase):
  """Logging testcases superclass.

  The class provides some operations common for testcases.
  """

  def setUp(self):
    super(LoggingStepBase, self).setUp()

    self._revision = 12345
    self._webkit_revision = 67890

  def _ConstructDefaultProcessor(self, log_processor_class,
                                 factory_properties=None,
                                 perf_expectations_path=None):
    factory_properties = factory_properties or {}
    factory_properties['perf_filename'] = perf_expectations_path
    factory_properties['perf_name'] = 'test-system'
    factory_properties['test_name'] = 'test-name'
    return log_processor_class(revision=self._revision, build_property={},
                               factory_properties=factory_properties,
                               webkit_revision=self._webkit_revision)

  def _ProcessLog(self, log_processor, logfile):  # pylint: disable=R0201
    for line in open(os.path.join(test_env.DATA_PATH, logfile)):
      log_processor.ProcessLine(line)

  def _CheckFileExistsWithData(self, logs, targetfile):
    self.assertTrue(targetfile in logs, 'File %s was not output.' % targetfile)
    self.assertTrue(logs[targetfile], 'File %s did not contain data.' %
                    targetfile)

  def _ConstructParseAndCheckLogfiles(self, inputfiles, logfiles,
                                      log_processor_class, *args, **kwargs):
    parser = self._ConstructDefaultProcessor(log_processor_class, *args,
                                             **kwargs)
    # Set custom percentiles if we're testing GraphingLogProcessor.
    if hasattr(parser, "_percentiles"):
      parser._percentiles = TEST_PERCENTILES
    for inputfile in inputfiles:
      self._ProcessLog(parser, inputfile)

    logs = parser.PerformanceLogs()
    for logfile in logfiles:
      self._CheckFileExistsWithData(logs, logfile)

    return logs

  def _ConstructParseAndCheckJSON(self, inputfiles, logfiles, subdir,
                                  log_processor_class, *args, **kwargs):

    logs = self._ConstructParseAndCheckLogfiles(inputfiles, logfiles,
                                                log_processor_class, *args,
                                                **kwargs)
    for filename in logfiles:
      actual = json.loads('\n'.join(logs[filename]))
      if subdir:
        path = os.path.join(test_env.DATA_PATH, subdir, filename)
      else:
        path = os.path.join(test_env.DATA_PATH, filename)
      expected = json.load(open(path))
      self.assertEqual(expected, actual, 'JSON data in %s did not match '
          'expectations.' % filename)


class BenchpressPerformanceTestStepTest(LoggingStepBase):
  def testOutputsSummaryBenchpress(self):
    input_files = ['benchpress_log']
    output_files = ['summary.dat']

    self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.BenchpressLogProcessor)

  def testBenchpressSummary(self):
    input_files = ['benchpress_log']
    summary_file = 'summary.dat'
    output_files = [summary_file]

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.BenchpressLogProcessor)

    actual = logs[summary_file][0]
    expected = '12345 469 165 1306 64 676 38 372 120 232 294 659 1157 397\n'
    self.assertEqual(expected, actual)


class GraphingLogProcessorTest(LoggingStepBase):
  def _TestPerfExpectations(self, perf_expectations_file):
    perf_expectations_path = os.path.join(
        test_env.DATA_PATH, perf_expectations_file)

    input_files = ['graphing_processor.log']
    graphfile = 'graphs.dat'
    output_files = [graphfile]

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.GraphingLogProcessor,
        factory_properties={'expectations': True, 'perf_id': 'tester'},
        perf_expectations_path=perf_expectations_path)

    actual = json.load('\n'.join(logs[graphfile]))
    expected = json.load(open(
        os.path.join(test_env.DATA_PATH, 'graphing_processor-graphs.dat')))
    self.assertEqual(expected, actual)
    return logs

  def testSummary(self):
    input_files = ['graphing_processor.log']
    output_files = ['%s-summary.dat' % graph for graph in ('commit_charge',
        'ws_final_total', 'vm_final_browser', 'vm_final_total',
        'ws_final_browser', 'processes', 'artificial_graph')]

    self._ConstructParseAndCheckJSON(input_files, output_files, None,
        process_log_utils.GraphingLogProcessor)

  def testFrameRateSummary(self):
    input_files = ['frame_rate_graphing_processor.log']
    output_files = ['%s-summary.dat' % g for g in ('blank', 'googleblog')]

    self._ConstructParseAndCheckJSON(input_files, output_files, 'frame_rate',
        process_log_utils.GraphingFrameRateLogProcessor)

  def testFrameRateGestureList(self):
    input_files = ['frame_rate_graphing_processor.log']
    output_files = ['%s_%s_%s.dat' % (self._revision, g, t)
                    for g in ('blank','googleblog') for t in ('fps', 'fps_ref')]

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.GraphingFrameRateLogProcessor)

    for filename in output_files:
      actual = ''.join(logs[filename])
      expected = open(os.path.join(test_env.DATA_PATH, 'frame_rate',
                                   filename)).read()
      self.assertEqual(actual, expected, 'Filename %s did not contain expected '
          'data.' % filename)

  def testGraphList(self):
    input_files = ['graphing_processor.log']
    graphfile = 'graphs.dat'
    output_files = [graphfile]

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.GraphingLogProcessor)

    actual = json.loads('\n'.join(logs[graphfile]))
    expected = json.load(open(
        os.path.join(test_env.DATA_PATH, 'graphing_processor-graphs.dat')))

    self.assertEqual(len(actual), len(expected))

    for graph in expected:
      self.assertTrue(graph['name'] in actual)
      for element in graph:
        self.assertEqual(actual[graph['name']][element], graph[element])

  def testHistogramGeometricMeanAndStandardDeviation(self):
    input_files = ['graphing_processor.log']
    summary_file = 'hist1-summary.dat'
    output_files = [summary_file]

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.GraphingLogProcessor)

    actual = json.loads('\n'.join(logs[summary_file]))
    expected = json.load(open(
        os.path.join(test_env.DATA_PATH, summary_file)))

    self.assertEqual(actual, expected, 'Filename %s did not contain expected '
        'data.' % summary_file)

  def testHistogramPercentiles(self):
    input_files = ['graphing_processor.log']
    summary_files = ['hist1_%s-summary.dat' % str(p) for p in TEST_PERCENTILES]
    output_files = summary_files

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.GraphingLogProcessor)

    for filename in output_files:
      actual = json.loads('\n'.join(logs[filename]))
      expected = json.load(open(os.path.join(test_env.DATA_PATH, filename)))
      self.assertEqual(actual, expected, 'Filename %s did not contain expected '
          'data.' % filename)

if __name__ == '__main__':
  unittest.main()
