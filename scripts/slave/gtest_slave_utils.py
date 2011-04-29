#!/usr/bin/env python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import re
import sys

from xml.dom import minidom


GENERATE_JSON_RESULTS_OPTIONS = [
    'builder_name', 'build_name', 'build_number', 'results_directory',
    'builder_base_url', 'webkit_dir', 'chrome_dir', 'test_results_server',
    'test_type', 'master_name']

INCREMENTAL_RESULTS_FILENAME = "incremental_results.json"
TIMES_MS_FILENAME = "times_ms.json"


class GTestResult(object):
  """A class that represents a single test result."""
  def __init__(self, failed=False, time=0):
    self.failed = failed
    self.time = time


class GTestUnexpectedDeathTracker(object):
  """A lightweight version of log parser that keeps track of running tests
  for unexpected timeout or crash."""

  def __init__(self):
    self._current_test = None
    self._test_start   = re.compile('\[\s+RUN\s+\] (\w+\.\w+)')
    self._test_ok      = re.compile('\[\s+OK\s+\] (\w+\.\w+)')
    self._test_fail    = re.compile('\[\s+FAILED\s+\] (\w+\.\w+)')

    self._failed_tests = set()

  def OnReceiveLine(self, line):
    results = self._test_start.search(line)
    if results:
      self._current_test = results.group(1)
      return

    results = self._test_ok.search(line)
    if results:
      self._current_test = ''
      return

    results = self._test_fail.search(line)
    if results:
      self._failed_tests.add(results.group(1))
      self._current_test = ''
      return

  def GetResultsMap(self):
    """Returns a map of GTestResults.  Returns an empty map if no current test
    has been recorded."""

    if not self._current_test:
      return dict()

    gtest_results_map = dict()
    for test in self._failed_tests:
      gtest_results_map[test] = GTestResult(failed=True)
    gtest_results_map[self._current_test] = GTestResult(failed=True)

    return gtest_results_map


def GetResultsMapFromXML(results_xml):
  """Parse the given results XML file and returns a map of GTestResults."""

  results_xml_file = None
  try:
    results_xml_file = open(results_xml)
  except IOError:
    logging.error("Cannot open file %s", results_xml)
    return dict()
  node = minidom.parse(results_xml_file).documentElement
  results_xml_file.close()

  gtest_results_map = dict()
  testcases = node.getElementsByTagName('testcase')

  for testcase in testcases:
    name = testcase.getAttribute('name')
    classname = testcase.getAttribute('classname')
    test_name = "%s.%s" % (classname, name)

    failures = testcase.getElementsByTagName('failure')
    elapsed = float(testcase.getAttribute('time'))
    gtest_results_map[test_name] = GTestResult(failed=bool(failures),
                                               time=elapsed)
  return gtest_results_map


def GenerateAndUploadJSONResults(gtest_results_map, options):
  """Generates a JSON results file from the given gtest_results_map and
  upload it to the results server if options.test_results_server is given.

  Args:
    gtest_results_map: A map of GTestResult.
    options: options for json generation. See GENERATE_JSON_RESULTS_OPTIONS
        and OptionParser's help messages below for expected options and their
        details.
  """

  if not gtest_results_map:
    logging.warn("No input results map was given.")
    return

  if not os.path.exists(options.webkit_dir):
    logging.warn("No options.webkit_dir (--webkit-dir) was given.")
    return

  # Make sure we have all the required options (set empty string otherwise).
  for opt in GENERATE_JSON_RESULTS_OPTIONS:
    if not getattr(options, opt, None):
      logging.warn("No value is given for option %s", opt)
      setattr(options, opt, '')

  from common import chromium_utils
  try:
    script_dir = chromium_utils.FindUpward(
        options.webkit_dir, 'WebKit', 'Tools', 'Scripts')
    sys.path.append(script_dir)
  except chromium_utils.PathNotFound, e:
    logging.error("Valid options.webkit_dir (--webkit-dir) must be "
                  "provided: %s", e)
    sys.exit(1)

  # pylint: disable=F0401
  from webkitpy.layout_tests.layout_package.json_results_generator \
      import JSONResultsGeneratorBase, TestResult

  if not os.path.exists(options.results_directory):
    os.makedirs(options.results_directory)

  test_results_map = dict()
  for (name, r) in gtest_results_map.iteritems():
    test_results_map[name] = TestResult(name,
                                        failed=r.failed,
                                        elapsed_time=r.time)

  print("Generating json: "
        "builder_name:%s, build_name:%s, build_number:%s, "
        "results_directory:%s, builder_base_url:%s, "
        "webkit_dir:%s, chrome_dir:%s "
        "test_results_server:%s, test_type:%s, master_name:%s" %
        (options.builder_name, options.build_name, options.build_number,
         options.results_directory, options.builder_base_url,
         options.webkit_dir, options.chrome_dir,
         options.test_results_server, options.test_type,
         options.master_name))

  from webkitpy.layout_tests import port
  port_obj = port.get()
  generator = JSONResultsGeneratorBase(port_obj,
      options.builder_name, options.build_name, options.build_number,
      options.results_directory, options.builder_base_url,
      test_results_map,
      svn_repositories=(('webkit', options.webkit_dir),
                        ('chrome', options.chrome_dir)),
      generate_incremental_results=True,
      test_results_server=options.test_results_server,
      test_type=options.test_type,
      master_name=options.master_name)
  generator.generate_json_output()
  generator.generate_times_ms_file()
  generator.upload_json_files([INCREMENTAL_RESULTS_FILENAME, TIMES_MS_FILENAME])


# For command-line testing.
def main():
  import optparse

  # Builder base URL where we have the archived test results.
  # (Note: to be deprecated)
  BUILDER_BASE_URL = "http://build.chromium.org/buildbot/gtest_results/"

  option_parser = optparse.OptionParser()
  option_parser.add_option("", "--test-type", default="",
                           help="Test type that generated the results XML,"
                                " e.g. unit-tests.")
  option_parser.add_option("", "--results-directory", default="./",
                           help="Output results directory source dir.")
  option_parser.add_option("", "--input-results-xml", default="",
                           help="Test results xml file (input for us)."
                                " default is TEST_TYPE.xml")
  option_parser.add_option("", "--builder-base-url", default="",
                           help=("A URL where we have the archived test "
                                  "results. (default=%sTEST_TYPE_results/)"
                                  % BUILDER_BASE_URL))
  option_parser.add_option("", "--builder-name",
                           default="DUMMY_BUILDER_NAME",
                           help="The name of the builder shown on the "
                                "waterfall running this script e.g. WebKit.")
  option_parser.add_option("", "--build-name",
                           default="DUMMY_BUILD_NAME",
                           help="The name of the builder used in its path, "
                                "e.g. webkit-rel.")
  option_parser.add_option("", "--build-number",
                           default="DUMMY_BUILD_NUMBER",
                           help="The build number of the builder running"
                                "this script.")
  option_parser.add_option("", "--test-results-server",
                           default="",
                           help="The test results server to upload the "
                                "results.")
  option_parser.add_option("--master-name", default="",
                           help="The name of the buildbot master. "
                                "Both test-results-server and master-name "
                                "need to be specified to upload the results "
                                "to the server.")
  option_parser.add_option("--webkit-dir", default=".",
                           help="The WebKit code base.")
  option_parser.add_option("--chrome-dir", default="",
                           help="The Chromium code base. If not given "
                                "${webkit_dir}/WebKit/chromium will be used.")

  options = option_parser.parse_args()[0]

  if not options.test_type:
    logging.error("--test-type needs to be specified.")
    sys.exit(1)

  if not options.input_results_xml:
    logging.error("--input-results-xml needs to be specified.")
    sys.exit(1)

  if options.test_results_server and not options.master_name:
    logging.warn("--test-results-server is given but "
                  "--master-name is not specified; the results won't be "
                  "uploaded to the server.")

  if not options.chrome_dir:
    options.chrome_dir = os.path.join(options.webkit_dir, "WebKit", "chromium")

  results_map = GetResultsMapFromXML(options.input_results_xml)
  GenerateAndUploadJSONResults(results_map, options)


if '__main__' == __name__:
  main()
