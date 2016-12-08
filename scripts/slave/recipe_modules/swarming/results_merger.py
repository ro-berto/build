# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

# These fields must appear in the test result output
REQUIRED = (
    'interrupted',
    'num_failures_by_type',
    'seconds_since_epoch',
    'tests',
    )

# These fields are optional, but must have the same value on all shards
OPTIONAL_MATCHING = (
    'path_delimiter',
    'build_number',
    'builder_name',
    'chromium_revision',
    'has_pretty_patch',
    'has_wdiff',
    'layout_tests_dir',
    'pixel_tests_enabled',
    )

# These fields are optional and will be summed together
OPTIONAL_COUNTS = (
    'fixable',
    'num_flaky',
    'num_passes',
    'num_regressions',
    'skips',
    'skipped',
    )


class MergeException(Exception):
  pass


def merge_test_results(shard_results_list):
  """ Merge list of results.

  Args:
    shard_results_list: list of results to merge. All the results must have the
      same format. Supported format are simplified JSON format & Chromium JSON
      test results format version 3 (see
      https://www.chromium.org/developers/the-json-test-results-format)

  Returns:
    a dictionary that represent the merged results. Its format follow the same
    format of all results in |shard_results_list|.
  """
  if 'seconds_since_epoch' in shard_results_list[0]:
    return _merge_json_test_result_format(shard_results_list)
  else:
    return _merge_simplified_json_format(shard_results_list)


def _merge_simplified_json_format(shard_results_list):
  # This code is specialized to the "simplified" JSON format that used to be
  # the standard for recipes.

  # These are the only keys we pay attention to in the output JSON.
  merged_results = {
    'successes': [],
    'failures': [],
    'valid': True,
  }

  for result_json in shard_results_list:
    successes = result_json.get('successes', [])
    failures = result_json.get('failures', [])
    valid = result_json.get('valid', True)

    if (not isinstance(successes, list) or not isinstance(failures, list) or
        not isinstance(valid, bool)):
      raise MergeException(
        'Unexpected value type in %s' % result_json)  # pragma: no cover

    merged_results['successes'].extend(successes)
    merged_results['failures'].extend(failures)
    merged_results['valid'] = merged_results['valid'] and valid
  return merged_results


def _merge_json_test_result_format(shard_results_list):
  # This code is specialized to the Chromium JSON test results format version 3:
  # https://www.chromium.org/developers/the-json-test-results-format

  # These are required fields for the JSON test result format version 3.
  merged_results = {
    'tests': {},
    'interrupted': False,
    'version': 3,
    'seconds_since_epoch': float('inf'),
    'num_failures_by_type': {
    }
  }

  # To make sure that we don't mutate existing shard_results_list.
  shard_results_list = copy.deepcopy(shard_results_list)
  for result_json in shard_results_list:
    result_json = copy.deepcopy(result_json)

    # Check the version first
    version = result_json.get('version', -1)
    if version != 3:
      raise MergeException(  # pragma: no cover - covered by results_merger_unittest
          'Unsupported version %s. Only version 3 is supported' % version)
    del result_json['version']

    # Check the results for each shard have the required keys
    for key in REQUIRED:
      if key not in result_json:
        raise MergeException(  # pragma: no cover - covered by results_merger_unittest
            'Invalid json test results (missing %s)' % key)

    # Traverse the result_json's test trie & merged_results's test tries in
    # DFS order & add the n to merged['tests'].
    curr_result_nodes_queue = [result_json['tests']]
    merged_results_nodes_queue = [merged_results['tests']]
    while curr_result_nodes_queue:
      curr_node = curr_result_nodes_queue.pop()
      merged_node = merged_results_nodes_queue.pop()
      for k, v in curr_node.iteritems():
        if k in merged_node:
          curr_result_nodes_queue.append(v)
          merged_results_nodes_queue.append(merged_node[k])
        else:
          merged_node[k] = v
    del result_json['tests']

    # If any where interrupted, we are interrupted.
    merged_results['interrupted'] |= result_json['interrupted']
    del result_json['interrupted']

    # Use the earliest seconds_since_epoch value
    merged_results['seconds_since_epoch'] = min(
        merged_results['seconds_since_epoch'],
        result_json['seconds_since_epoch'])
    del result_json['seconds_since_epoch']

    # Sum the number of failure types
    for result_type, count in result_json['num_failures_by_type'].iteritems():
      merged_results['num_failures_by_type'].setdefault(result_type, 0)
      merged_results['num_failures_by_type'][result_type] += count
    del result_json['num_failures_by_type']

    # Optional values must match
    for optional in OPTIONAL_MATCHING:
      optional_value = result_json.get(optional, None)
      if optional not in merged_results:
        merged_results[optional] = optional_value
      elif merged_results[optional] != optional_value:
        raise MergeException(  # pragma: no cover - covered by results_merger_unittest
            'Inconsistent %s: %s %s' %
            (optional,
             merged_results[optional],
             optional_value))
      if optional in result_json:
        del result_json[optional]

    # Optional value counts
    for optional in OPTIONAL_COUNTS:
      if optional in result_json:
        merged_results[optional] = (  # pragma: no cover - covered by results_merger_unittest
            merged_results.get(optional, 0) + result_json[optional])
        del result_json[optional]  # pragma: no cover - covered by results_merger_unittest

    if len(result_json) != 0:
      raise MergeException(  # pragma: no cover - covered by results_merger_unittest
          'Unmergable values %s' % result_json.keys())

  for optional in OPTIONAL_MATCHING:
    if optional in merged_results and merged_results[optional] is None:
      del merged_results[optional]

  return merged_results
