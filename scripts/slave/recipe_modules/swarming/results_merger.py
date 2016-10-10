# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy


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
      raise Exception(
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
    'path_delimiter': '',
    'version': 3,
    'seconds_since_epoch': float('inf'),
    'num_failures_by_type': {
    }
  }
  # To make sure that we don't mutate existing shard_results_list.
  shard_results_list = copy.deepcopy(shard_results_list)
  for result_json in shard_results_list:
    if not ('tests' in result_json and
            'interrupted' in result_json and
            'path_delimiter' in result_json and
            'version' in result_json and
            'seconds_since_epoch' in result_json and
            'num_failures_by_type' in result_json):
      raise Exception('Invalid json test results')

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

    # Update the rest of the fields for merged_results.
    merged_results['interrupted'] |= result_json['interrupted']
    if not merged_results['path_delimiter']:
      merged_results['path_delimiter'] = result_json['path_delimiter']
    elif merged_results['path_delimiter'] != result_json['path_delimiter']:
      raise Exception(  # pragma: no cover - covered by results_merger_unittest
          'Incosistent path delimiter: %s %s' %
          (merged_results['path_delimiter'],
           result_json['path_delimiter']))
    if result_json['version'] != 3:
      raise Exception(  # pragma: no cover - covered by results_merger_unittest
          'Only version 3 of json test result format is supported')
    merged_results['seconds_since_epoch'] = min(
        merged_results['seconds_since_epoch'],
        result_json['seconds_since_epoch'])
    for result_type, count in result_json['num_failures_by_type'].iteritems():
      merged_results['num_failures_by_type'].setdefault(result_type, 0)
      merged_results['num_failures_by_type'][result_type] += count
  return merged_results
