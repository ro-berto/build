# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import collect_v8_task
import json
import unittest

from pyfakefs import fake_filesystem_unittest


class BadShardsTestCase(unittest.TestCase):

  def test_initiate_bad_shards(self):
    bad_shards = collect_v8_task.BadShards()
    self.assertEqual(bad_shards.missing, [])
    self.assertEqual(bad_shards.incomplete, [])

  def test_add_incomplete_shard(self):
    bad_shards = collect_v8_task.BadShards()
    bad_shards.add_incomplete('example')
    self.assertEqual(bad_shards.missing, [])
    self.assertEqual(bad_shards.incomplete, ['example'])

  def test_add_missing_shard(self):
    bad_shards = collect_v8_task.BadShards()
    bad_shards.add_missing('example')
    self.assertEqual(bad_shards.missing, ['example'])
    self.assertEqual(bad_shards.incomplete, [])

  def test_check_bad_shards_not_empty(self):
    bad_shards = collect_v8_task.BadShards()
    self.assertFalse(bad_shards.not_empty())
    bad_shards.add_missing('example')
    self.assertTrue(bad_shards.not_empty())

  def test_return_bad_shards_as_string(self):
    bad_shards = collect_v8_task.BadShards()
    bad_shards.add_incomplete('incomplete example')
    bad_shards.add_missing('missing example')
    self.assertEqual(bad_shards.as_str(), 'incomplete example, missing example')

  def test_return_missing_shards_count(self):
    bad_shards = collect_v8_task.BadShards()
    bad_shards.add_missing('example 1')
    bad_shards.add_missing('example 2')
    self.assertEqual(bad_shards.missing_count(), 2)


class AggregatedResultsTestCase(unittest.TestCase):

  def test_initiate_aggregated_results(self):
    aggregated_results = collect_v8_task.AggregatedResults(10)
    self.assertEqual(aggregated_results.slowest_tests, [])
    self.assertEqual(aggregated_results.results, [])
    self.assertEqual(aggregated_results.test_total, 0)
    self.assertEqual(aggregated_results.slow_tests_cutoff, 10)

  def test_append_json_data(self):
    aggregated_results = collect_v8_task.AggregatedResults(10)
    self.assertEqual(aggregated_results.slowest_tests, [])
    self.assertEqual(aggregated_results.results, [])
    self.assertEqual(aggregated_results.test_total, 0)
    self.assertEqual(aggregated_results.slow_tests_cutoff, 10)
    aggregated_results.append({
        'slowest_tests': 'x',
        'results': 'y',
        'test_total': 1
    })
    self.assertEqual(aggregated_results.slowest_tests, ['x'])
    self.assertEqual(aggregated_results.results, ['y'])
    self.assertEqual(aggregated_results.test_total, 1)
    self.assertEqual(aggregated_results.slow_tests_cutoff, 10)

  def test_return_aggregated_tests_as_json(self):
    aggregated_results = collect_v8_task.AggregatedResults(10)
    aggregated_results.append({
        'slowest_tests': [
            {
                'name': 'a',
                'duration': 10
            },
            {
                'name': 'b',
                'duration': 30
            },
            {
                'name': 'c',
                'duration': 20
            },
        ],
        'results': 'y',
        'test_total': 3
    })
    self.assertEqual(
        aggregated_results.as_json(['tag 1', 'tag 3', 'tag 2']), {
            'slowest_tests': [{
                'duration': 30,
                'name': 'b'
            }, {
                'duration': 20,
                'name': 'c'
            }, {
                'duration': 10,
                'name': 'a'
            }],
            'results': ['y'],
            'test_total': 3,
            'tags': ['tag 1', 'tag 2', 'tag 3']
        })


class TaskCollectorTestCase(fake_filesystem_unittest.TestCase):

  def test_initiate_task_collector(self):
    task_collector = collect_v8_task.TaskCollector()
    self.assertEqual(task_collector.warnings, [])

  def test_emit_warnings(self):
    task_collector = collect_v8_task.TaskCollector()
    self.assertEqual(task_collector.warnings, [])
    task_collector.emit_warning(title='title example', log='log example')
    self.assertEqual(task_collector.warnings,
                     [['title example', 'log example']])

  def test_get_shards_info(self):
    self.setUpPyfakefs(allow_root_user=True)
    self.fs.create_file('/summary.json')

    summary_content = {"shards": ["a", "b", "c"]}
    with open('/summary.json', 'w') as f:
      json.dump(summary_content, f)

    task_collector = collect_v8_task.TaskCollector()
    shards = task_collector.get_shards_info(output_dir='/')
    self.assertEqual(shards, ['a', 'b', 'c'])

  def test_get_shards_info_without_file(self):
    task_collector = collect_v8_task.TaskCollector()
    self.assertEqual(task_collector.warnings, [])
    shards = task_collector.get_shards_info(output_dir='/')
    self.assertIsNone(shards)
    self.assertEqual(task_collector.warnings, [[
        'summary.json is missing or can not be read',
        'Something is seriously wrong with swarming_client/ or the bot.'
    ]])

  def test_merge_shard_results_without_shards(self):
    task_collector = collect_v8_task.TaskCollector()
    shard_results = task_collector.merge_shard_results(
        output_dir='/', shards=None, options=None)
    self.assertIsNone(shard_results)

  def test_merge_shard_output(self):
    self.setUpPyfakefs(allow_root_user=True)
    self.fs.create_file('/123/example_shard.json')

    summary_content = {"result": "example result"}
    with open('/123/example_shard.json', 'w') as f:
      json.dump(summary_content, f)

    task_collector = collect_v8_task.TaskCollector()
    loaded_shard = task_collector.load_shard_json(
        output_dir='/', task_id='123', file_name='example_shard.json')
    self.assertEqual(loaded_shard, {"result": "example result"})

  def test_merge_shard_output_exception(self):
    task_collector = collect_v8_task.TaskCollector()
    loaded_shard = task_collector.load_shard_json(
        output_dir='/', task_id='123', file_name='example_shard.json')
    self.assertIsNone(loaded_shard)

  def test_merge_shard_results_when_all_shards_fail(self):
    Options = collections.namedtuple('options', ['slow_tests_cutoff'])
    example_options = Options(slow_tests_cutoff=10)
    example_shards = [{
        'task_id': 'a',
        'exit_code': 0
    }, {
        'task_id': 'b',
        'exit_code': 1
    }]
    task_collector = collect_v8_task.TaskCollector()
    merged_shard_result = task_collector.merge_shard_results(
        output_dir='/', shards=example_shards, options=example_options)
    self.assertEqual(
        merged_shard_result, {
            'slowest_tests': [],
            'results': [],
            'tags': ['UNRELIABLE_RESULTS'],
            'test_total': 0
        })

  def test_merge_test_results(self):
    example_shards = [{
        'task_id': 'a',
        'exit_code': 0
    }, {
        'task_id': 'b',
        'exit_code': 1
    }]
    example_merged_test_output = {
        'slowest_tests': [],
        'results': [],
        'tags': ['UNRELIABLE_RESULTS'],
        'test_total': 0
    }

    self.setUpPyfakefs(allow_root_user=True)
    self.fs.create_file('/merged_output.json')

    with open('/merged_output.json', 'w') as f:
      json.dump(example_merged_test_output, f)

    Options = collections.namedtuple(
        'options', ['merged_test_output', 'slow_tests_cutoff'])
    example_options = Options(
        merged_test_output='/merged_output.json', slow_tests_cutoff=10)
    task_collector = collect_v8_task.TaskCollector()
    task_collector.merge_test_results(
        output_dir='/', shards=example_shards, options=example_options)

    with open(example_options.merged_test_output, 'r') as f:
      self.assertEqual(
          json.load(f), {
              'slowest_tests': [],
              'results': [],
              'tags': ['UNRELIABLE_RESULTS'],
              'test_total': 0
          })


if __name__ == '__main__':
  unittest.main()
