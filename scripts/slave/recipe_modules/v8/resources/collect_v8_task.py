#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import optparse
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

from slave import slave_utils

MISSING_SHARDS_MSG = r"""Missing results from the following shard(s): %s

It can happen in following cases:
  * Test failed to start (missing *.dll/*.so dependency for example)
  * Test crashed or hung
  * Task expired because there are not enough bots available and are all used
  * Swarming service experiences problems

Please examine logs to figure out what happened.
"""


class BadShards:

  def __init__(self):
    self.missing = []
    self.incomplete = []

  def add_incomplete(self, shard):
    self.incomplete.append(shard)

  def add_missing(self, shard):
    self.missing.append(shard)

  def not_empty(self):
    return self.missing or self.incomplete

  def as_str(self):
    return ', '.join(map(str, sorted(self.missing + self.incomplete)))

  def missing_count(self):
    return len(self.missing)


class AggregatedResults:

  def __init__(self, slow_tests_cutoff):
    self.archs = []
    self.modes = []
    self.slowest_tests = []
    self.results = []
    self.slow_tests_cutoff = slow_tests_cutoff

  def append(self, json_data):
    # On continuous bots, the test driver outputs exactly one item in the
    # test results list for one architecture.
    assert len(json_data) == 1
    self.archs.append(json_data[0]['arch'])
    self.modes.append(json_data[0]['mode'])
    self.slowest_tests.extend(json_data[0]['slowest_tests'])
    self.results.extend(json_data[0]['results'])

  def as_json(self, tags):
    # Each shard must have used the same arch and mode configuration.
    assert len(set(self.archs)) == 1
    assert len(set(self.modes)) == 1
    sorted_tests = sorted(
        self.slowest_tests, key=lambda t: t['duration'], reverse=True)
    return [{
        'arch': self.archs[0],
        'mode': self.modes[0],
        'slowest_tests': sorted_tests[:self.slow_tests_cutoff],
        'results': self.results,
        'tags': sorted(tags),
    }]


def emit_warning(title, log=None):
  print '@@@STEP_WARNINGS@@@'
  print title
  if log:
    slave_utils.WriteLogLines(title, log.split('\n'))


def get_shards_info(output_dir):
  # summary.json is produced by swarming.py itself. We are mostly interested
  # in the number of shards.
  try:
    with open(os.path.join(output_dir, 'summary.json')) as f:
      summary = json.load(f)
    return summary['shards']
  except (IOError, ValueError):
    emit_warning(
        'summary.json is missing or can not be read',
        'Something is seriously wrong with swarming_client/ or the bot.')
    return None


def merge_shard_results(output_dir, shards, options):
  """Reads JSON test output from all shards and combines them into one.

  Also merges sancov coverage data if coverage_dir is spefied.

  Returns dict with merged test output on success or None on failure. Emits
  annotations.
  """
  if not shards:
    return None

  # Merge all JSON files together.

  tags = set()
  aggregated_results = AggregatedResults(options.slow_tests_cutoff)
  bad_shards = BadShards()
  for index, result in enumerate(shards):
    if result is not None:
      if int(result.get('exit_code', 0)):
        # When receiving a sigterm, the test runner terminates gracefully
        # with json output, but has a non-zero return code.
        bad_shards.add_incomplete(index)
      json_data = load_shard_json(output_dir, result['task_id'], 'output.json')
      if json_data:
        aggregated_results.append(json_data)
        continue
    bad_shards.add_missing(index)

  # If some shards are missing, make it known. Continue parsing anyway. Step
  # should be red anyway, since swarming.py return non-zero exit code in that
  # case.
  if bad_shards.not_empty():
    # Not all tests run, combined JSON summary can not be trusted.
    tags.add('UNRELIABLE_RESULTS')
    as_str = bad_shards.as_str()
    emit_warning('some shards did not complete: %s' % as_str,
                 MISSING_SHARDS_MSG % as_str)

  # Handle the case when all shards fail. Return minimalistic dict that has all
  # fields that a calling recipe expects to avoid recipe-level exceptions.
  if bad_shards.missing_count() == len(shards):
    return [{'slowest_tests': [], 'results': [], 'tags': sorted(tags)}]

  return aggregated_results.as_json(tags)


def merge_test_results(output_dir, shards, options):
  with open(options.merged_test_output, 'wb') as f:
    merged_data = merge_shard_results(output_dir, shards, options)
    json.dump(merged_data, f, separators=(',', ':'))


def merge_coverage_data(output_dir, shards, options):
  # Merge coverage data if specified.
  if options.coverage_dir:
    for index, result in enumerate(shards):
      exit_code = subprocess.call([
          sys.executable, '-u', options.sancov_merger, '--coverage-dir',
          options.coverage_dir, '--swarming-output-dir',
          os.path.join(output_dir, result['task_id'])
      ])
      if exit_code:
        emit_warning('error when merging coverage data of shard %d' % index)


def load_shard_json(output_dir, task_id, file_name):
  """Reads JSON output of a single shard."""
  # 'output.json' is set in v8/testing.py, V8SwarmingTest.
  path = os.path.join(output_dir, task_id, file_name)
  try:
    with open(path) as f:
      return json.load(f)
  except (IOError, ValueError):
    print >> sys.stderr, 'Missing or invalid v8 JSON file: %s' % path
    return None


def swarming_cmd(swarming_args, options):
  # Prepare a directory to store JSON files fetched from isolate.
  task_output_dir = tempfile.mkdtemp(
      suffix='_swarming', dir=options.temp_root_dir)
  # Start building the command line for swarming.py.
  cmd = [
      'swarming',
  ]

  cmd.extend(swarming_args)
  cmd.extend([
      '-output-dir',
      task_output_dir,
      '-task-summary-json',
      os.path.join(task_output_dir, 'summary.json'),
  ])
  return cmd, task_output_dir


def parse_args(args):
  # Split |args| into options for shim and options for swarming.py script.
  if '--' in args:
    index = args.index('--')
    shim_args, swarming_args = args[:index], args[index + 1:]
  else:
    shim_args, swarming_args = args, []

  # Parse shim's own options.
  parser = optparse.OptionParser()
  parser.add_option('--temp-root-dir', default=tempfile.gettempdir())
  parser.add_option('--merged-test-output')
  parser.add_option('--slow-tests-cutoff', type="int", default=100)
  parser.add_option('--coverage-dir')
  parser.add_option('--sancov-merger')
  options, extra_args = parser.parse_args(shim_args)

  # Validate options.
  if extra_args:
    parser.error('Unexpected command line arguments')
  if options.coverage_dir and not options.sancov_merger:
    parser.error('--sancov-merger is required for merging coverage data')

  return options, swarming_args


def main(args):
  options, swarming_args = parse_args(args)
  cmd, output_dir = swarming_cmd(swarming_args, options)

  exit_code = 1
  try:
    # Run the real script, regardless of an exit code try to find and parse
    # JSON output files, since exit code may indicate that the isolated task
    # failed, not the swarming.py invocation itself.
    exit_code = subprocess.call(cmd)

    # Output parsing should not change exit code no matter what, so catch any
    # exceptions and just log them.
    try:
      shards = get_shards_info(output_dir)
      merge_test_results(output_dir, shards, options)
      merge_coverage_data(output_dir, shards, options)
    except Exception:
      emit_warning('failed to process v8 output JSON', traceback.format_exc())

  finally:
    shutil.rmtree(output_dir, ignore_errors=True)

  return exit_code


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
