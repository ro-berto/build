#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""See README.md for usage instructions.

This file heavily modified from build/scripts/slave/gtest_slave_utils.py and
is intended to replace it as all tests move to swarming.
TODO(estaab): Remove build/scripts/slave/gtest.* once this is fully deployed.
"""


import json
import logging
import optparse
import os
import sys

from json_results_generator import JSONResultsGenerator
import test_result
import test_results_uploader


FULL_RESULTS_FILENAME = 'full_results.json'
TIMES_MS_FILENAME = 'times_ms.json'


def get_results_map_from(contents):
  """Returns a map of test results given a gtest json.

  Returns:
    {'Test.Name': [TestResult, TestResult, ...], 'Test.Name2': [...]}
  """
  test_results_map = {}
  for test in contents.get('disabled_tests', []):
    test_results_map[test_result.canonical_name(test)] = [
        test_result.TestResult(test, status='SKIPPED')]
  for result_sets in contents.get('per_iteration_data', []):
    for test, results in result_sets.iteritems():
      for result in results:
        result = test_result.TestResult(
            test,
            status=result['status'],
            elapsed_time=result.get('elapsed_time_ms', 0) / 1000.)
        test_results_map.setdefault(test, []).append(result)
  return test_results_map


def generate_json_results_file_for_json(
    results_json, builder_name, build_number,
    results_directory, chrome_revision, master_name, build_id):
  """Generates JSON results file from the given |results_json|.

  Args:
    results_json: the raw test results object that follows full json results
      format.

  Returns:
    A list that contains a single tuple (<file name>, <file path>). The tuple
    represents the full test results file.
  """
  if not os.path.exists(results_directory):
    os.makedirs(results_directory)
  json_results_file_path = os.path.abspath(
      os.path.join(results_directory, FULL_RESULTS_FILENAME))
  results_json['builder_name'] = builder_name
  results_json['build_number'] = build_number
  results_json['build_id'] = build_id
  results_json['chromium_revision'] = chrome_revision
  results_json['master_name'] = master_name
  with open(json_results_file_path, 'w') as f:
    json.dump(results_json, f)
  return [(FULL_RESULTS_FILENAME, json_results_file_path)]


def generate_json_results_file_for_gtest(
    gtest_json, builder_name, build_number, results_directory, chrome_revision,
    master_name, build_id):
  """Generates JSON results files from the given |gtest_json|.

  Args:
    gtest_json: the raw test results object that follows GTest format.

  Returns:
    A list of tuples (<file name>, <file path>). The list has two
    elements: the first represent the full test results file, and the
    second is is the times_ms.json file.
  """
  contents = json.loads(gtest_json)
  test_results_map = get_results_map_from(contents)
  if not os.path.exists(results_directory):
    os.makedirs(results_directory)

  logging.info(
      'Generating json: '
      'builder_name:%s, build_number:%s, '
      'results_directory:%s, '
      'chrome_revision:%s '
      'master_name:%s '
      'build_id: %s' %
      (builder_name, build_number,
       results_directory,
       chrome_revision,
       master_name, build_id))

  # TODO(estaab): This doesn't need to be an object. Make it a simple function.
  generator = JSONResultsGenerator(
      builder_name, build_number,
      results_directory,
      test_results_map,
      master_name=master_name,
      test_locations=contents.get('test_locations'),
      build_id=build_id)
  generator.generate_json_output()
  generator.generate_times_ms_file()
  return [(f, os.path.join(results_directory, f)) for f in
          (FULL_RESULTS_FILENAME, TIMES_MS_FILENAME)]


def main(args):
  option_parser = optparse.OptionParser()
  option_parser.add_option('--test-type',
                           help='Test type that generated the results json,'
                                ' e.g. unit-tests.')
  option_parser.add_option('--results-directory', default=os.getcwd(),
                           help='Output results directory source dir.')
  option_parser.add_option('--input-json',
                           help='Test results json file (input for us).')
  option_parser.add_option('--builder-name',
                           default='DUMMY_BUILDER_NAME',
                           help='The name of the builder shown on the '
                                'waterfall running this script e.g. WebKit.')
  option_parser.add_option('--build-number',
                           help='The build number of the builder running'
                                'this script.')
  option_parser.add_option('--build-id',
                           type=int,
                           help='The buildbucket build ID of the builder running'
                                'this script.')
  option_parser.add_option('--test-results-server',
                           help='The test results server to upload the '
                                'results.')
  option_parser.add_option('--master-name',
                           help='The name of the buildbot master. '
                                'Both test-results-server and master-name '
                                'need to be specified to upload the results '
                                'to the server.')
  option_parser.add_option('--chrome-revision', default='0',
                           help='The Chromium revision being tested. If not '
                                'given, defaults to 0.')

  options = option_parser.parse_args(args)[0]
  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  if not options.test_type:
    option_parser.error('--test-type needs to be specified.')
    return 1

  if not options.input_json:
    option_parser.error('--input-json needs to be specified.')
    return 1

  if options.test_results_server and not options.master_name:
    logging.warn('--test-results-server is given but '
                 '--master-name is not specified; the results won\'t be '
                 'uploaded to the server.')

  with file(options.input_json) as json_file:
    results_json = json_file.read()

  content = json.loads(results_json)
  if content.get('version', 0) >= 3:
    logging.info('Input JSON file probably has full json results format')
    files = generate_json_results_file_for_json(
      content, builder_name=options.builder_name,
      build_number=options.build_number,
      results_directory=options.results_directory,
      chrome_revision=options.chrome_revision,
      master_name=options.master_name,
      build_id=options.build_id)
  else:
    logging.info(
        'Input JSON file probably has gtest format. Converting to full json'
        ' results format')
    files = generate_json_results_file_for_gtest(
        results_json, builder_name=options.builder_name,
        build_number=options.build_number,
        results_directory=options.results_directory,
        chrome_revision=options.chrome_revision,
        master_name=options.master_name,
        build_id=options.build_id)

  # Upload to a test results server if specified.
  if options.test_results_server and options.master_name:
    logging.info('Uploading JSON files for builder "%s" to server "%s"' % (
        options.builder_name, options.test_results_server))
    attrs = [('builder', options.builder_name),
             ('testtype', options.test_type),
             ('master', options.master_name)]

    # Set uploading timeout in case appengine server is having problem.
    # 120 seconds are more than enough to upload test results.
    test_results_uploader.upload_test_results(
        options.test_results_server, attrs, files, 120)

  # This logging is here to help debug why test results sometimes take so long
  # to upload. See crbug.com/795118
  logging.info('Done processing test results data')
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
