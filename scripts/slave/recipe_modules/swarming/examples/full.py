# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

DEPS = [
  'isolate',
  'recipe_engine/buildbucket',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'swarming',
  'swarming_client',
  'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

PROPERTIES = {
  'platforms': Property(default=('win',)),
  'show_outputs_ref_in_collect_step': Property(default=True),
  'show_shards_in_collect_step': Property(default=False),
  'gtest_task': Property(default=False),
  'isolated_script_task': Property(default=False),
  'merge': Property(default=None),
  'trigger_script': Property(default=None),
  'named_caches': Property(default=None),
  'service_account': Property(default=None),
  'wait_for_tasks': Property(default=None),
  'use_go_client': Property(default=False),
}

def RunSteps(api, platforms, show_outputs_ref_in_collect_step,
             show_shards_in_collect_step, gtest_task, isolated_script_task,
             merge, trigger_script, named_caches, service_account,
             wait_for_tasks, use_go_client):
  # Checkout swarming client.
  api.swarming_client.checkout('master')

  # Ensure swarming_client version is fresh enough.
  api.swarming.check_client_version(step_test_data=(0, 8, 6))

  # Configure isolate & swarming modules (this is optional).
  api.isolate.isolate_server = 'https://isolateserver-dev.appspot.com'
  api.swarming.swarming_server = 'https://chromium-swarm-dev.appspot.com'
  api.swarming.add_default_tag('master:tryserver')
  api.swarming.default_expiration = 60*60
  api.swarming.default_hard_timeout = 60*60
  api.swarming.default_io_timeout = 20*60
  api.swarming.default_idempotent = True
  api.swarming.default_priority = 30
  api.swarming.default_user = 'joe'
  api.swarming.set_default_env('TESTING', '1')
  api.swarming.verbose = True
  api.swarming.task_output_stdout = 'json'
  api.swarming.service_account_json = (
      '/creds/service_accounts/service-account-chromium-builder.json')

  api.swarming.set_default_dimension('inexistent', None)

  api.swarming.show_shards_in_collect_step = show_shards_in_collect_step
  api.swarming.show_outputs_ref_in_collect_step = (
      show_outputs_ref_in_collect_step)

  if use_go_client:
    api.swarming.use_go_client = use_go_client

  try:
    # Testing ReadOnlyDict.__setattr__() coverage.
    api.swarming.default_dimensions['invalid'] = 'foo'
  except TypeError:
    pass
  try:
    api.swarming.default_env['invalid'] = 'foo'
  except TypeError:
    pass

  # Create a temp dir to put *.isolated files into.
  temp_dir = api.path.mkdtemp('hello_isolated_world')

  # Prepare a bunch of swarming tasks to run hello_world on multiple platforms.
  tasks = []
  for platform in platforms:
    # Isolate example hello_world.isolate from swarming client repo.
    # TODO(vadimsh): Add a thin wrapper around isolate.py to 'isolate' module?
    step_result = api.python(
        'archive for %s' % platform,
        api.swarming_client.path.join('isolate.py'),
        [
          'archive',
          '--isolate', api.swarming_client.path.join(
              'example', 'payload', 'hello_world.isolate'),
          '--isolated', temp_dir.join('hello_world.isolated'),
          '--isolate-server', api.isolate.isolate_server,
          '--config-variable', 'OS', platform,
          '--verbose',
        ], stdout=api.raw_io.output_text())
    # TODO(vadimsh): Pass result from isolate.py though --output-json option.
    isolated_hash = step_result.stdout.split()[0].strip()

    # Create a task to run the isolated file on swarming, set OS dimension.
    # Also generate code coverage for multi-shard case by triggering multiple
    # shards on Linux.
    if gtest_task:
      task = api.swarming.gtest_task(
          'hello_world', isolated_hash,
          task_output_dir=temp_dir.join('task_output_dir'),
          test_launcher_summary_output=api.test_utils.gtest_results(
              add_json_log=False),
          merge=merge)
    elif isolated_script_task:
      task = api.swarming.isolated_script_task(
          'hello_world', isolated_hash,
          task_output_dir=temp_dir.join('task_output_dir'),
          merge=merge, trigger_script=trigger_script, env={
              'IS_GTEST': '', 'IS_SCRIPTTEST': 'True'})
    else:
      task = api.swarming.task('hello_world', isolated_hash,
                              task_output_dir=temp_dir.join('task_output_dir'),
                              named_caches=named_caches,
                              service_account=service_account,
                              cipd_packages=[
                                ('', 'cool/package', 'vers'),
                              ])
    task.dimensions['os'] = api.swarming.prefered_os_dimension(platform)
    task.shards = 2 if platform == 'linux' else 1
    task.tags.add('os:' + platform)
    if api.swarming_client.get_script_version('swarming.py') >= (0, 8, 6):
      task.cipd_packages.append(
        ('bin', 'super/awesome/pkg', 'git_revision:deadbeef'))
    tasks.append(task)

  # Launch all tasks.
  for task in tasks:
    step_result = api.swarming.trigger_task(task)
    assert len(task.get_task_shard_output_dirs()) == task.shards
    assert step_result.swarming_task in tasks

  # Recipe can do something useful here locally while tasks are
  # running on swarming.
  api.step('local step', ['echo', 'running something locally'])

  if wait_for_tasks:
    task_ids = [
        task.get_task_ids() for task in tasks
    ]

    api.swarming.wait_for_finished_task_set(task_ids)
    api.swarming.wait_for_finished_task_set(task_ids)
    return

  # Wait for all tasks to complete.
  for task in tasks:
    step_result = api.swarming.collect_task(task)
    assert step_result.swarming_task in tasks

  api.swarming.report_stats()

  # Cleanup.
  api.file.rmtree('remove temp dir', temp_dir)


def GenTests(api):
  yield (
      api.test('basic') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
            'hash_for_linux hello_world.isolated')) +
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text('hash_for_mac hello_world.isolated')) +
      api.properties(platforms=('win', 'linux', 'mac')))

  yield (
      api.test('wait_for_tasks') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
            'hash_for_linux hello_world.isolated')) +
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text('hash_for_mac hello_world.isolated')) +
      # This is probably how you'd use the test api; testing what happens if one
      # set of tasks finishes first. This example code doesn't care what is
      # returned, but calling code of this usually does.
      api.swarming.wait_for_finished_task_set([
          ([['110000', '110100']], 1),
          ([['100000'],
            ['130000']], 1),
      ]) +
      api.properties(platforms=('win', 'linux', 'mac'), wait_for_tasks=True) +
      api.post_process(post_process.Filter(
          'wait for tasks', 'wait for tasks (2)')))

  for exp in [True, False]:
    yield (
        api.test('basic_luci' + ('_experimental' if exp else '')) +
        api.runtime(is_luci=True, is_experimental=exp) +
        api.step_data(
            'archive for win',
            stdout=api.raw_io.output_text(
              'hash_for_win hello_world.isolated')) +
        api.step_data(
            'archive for linux',
            stdout=api.raw_io.output_text(
              'hash_for_linux hello_world.isolated')) +
        api.step_data(
            'archive for mac',
            stdout=api.raw_io.output_text(
              'hash_for_mac hello_world.isolated')) +
        api.properties(platforms=('win', 'linux', 'mac')))

  yield (
      api.test('named_caches') +
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text('hash_for_mac hello_world.isolated')) +
      api.properties(
          platforms=('mac',),
          named_caches={'foo': 'cache/foo', 'bar': 'cache/bar'}))

  yield (
      api.test('service_account') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
            'hash_for_linux hello_world.isolated')) +
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text('hash_for_mac hello_world.isolated')) +
      api.properties(
          platforms=('win', 'linux', 'mac',),
          service_account='test@example.com'))

  yield (
      api.test('gerrit_trybot') +
      api.buildbucket.try_build(
          project='chromium',
          builder='linux',
          git_repo='https://chromium.googlesource.com/chromium/src') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')))

  yield (
      api.test('show_shards_in_collect_step') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.properties(show_shards_in_collect_step=True))

  yield (
      api.test('show_outputs_ref_in_collect_step') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.properties(show_outputs_ref_in_collect_step=False))

  data = {
    'shards': [
      {
        '': '',
      }
    ]
  }

  yield (
      api.test('gtest_with_outputs_ref') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.swarming.canned_summary_output() +
          api.test_utils.canned_gtest_output(True))
    )

  data = {
    'shards': [
      {
        'duration': 120.0,
        'state': 'COMPLETED',
      }
    ]
  }

  yield (
      api.test('gtest_with_duration') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.swarming.summary(data) +
          api.test_utils.canned_gtest_output(True))
    )

  data = api.swarming.canned_summary_output_raw(shards=4)
  data['shards'][2]['completed_ts'] = '2014-09-25T01:49:23.123'
  data['shards'][3]['completed_ts'] = '2014-09-25T01:48:22.345'

  yield (
      api.test('gtest_with_long_task') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.swarming.summary(data) +
          api.test_utils.canned_gtest_output(True))
    )

  yield (
      api.test('gtest_with_many_failures') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.test_utils.simulated_gtest_output(
              failed_test_names=['test-%d' % i for i in xrange(100)])) +
      api.properties(gtest_task=True)
    )

  data = {
    'shards': [
      {
        'abandoned_ts': '2014-09-25T01:41:00.123',
        'bot_id': 'vm30',
        'completed_ts': None,
        'created_ts': '2014-09-25T01:41:00.123',
        'duration': 60,
        'failure': False,
        'id': '148aa78d7aa0100',
        'internal_failure': False,
        'outputs_ref': None,
        'modified_ts': '2014-09-25 01:42:00',
        'name': 'heartbeat-canary-2014-09-25_01:41:55-os=Windows',
        'outputs': [],
        'started_ts': '2014-09-25T01:42:11.123',
        'state': 'EXPIRED',
        'try_number': None,
        'user': 'unknown',
      }
    ],
  }

  data['shards'][0]['state'] = 'EXPIRED'
  yield (
      api.test('swarming_expired_new') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data('hello_world on Windows-7-SP1', api.swarming.summary(data)))
  yield (
      api.test('isolated_script_expired_new') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.raw_io.output_dir({'summary.json': json.dumps(data)})) +
      api.properties(isolated_script_task=True))

  data['shards'][0]['state'] = 'TIMED_OUT'
  yield (
      api.test('swarming_timeout_new') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data('hello_world on Windows-7-SP1', api.swarming.summary(data)))
  yield (
      api.test('isolated_script_timeout_new') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.raw_io.output_dir({'summary.json': json.dumps(data)})) +
      api.properties(isolated_script_task=True))

  data['shards'][0]['state'] = 'COMPLETED'
  data['shards'][0]['exit_code'] = '1'
  yield (
      api.test('isolated_script_non_zero_exit_status') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.raw_io.output_dir({'summary.json': json.dumps(data)}) +
          api.swarming.summary(data)) +
      api.properties(isolated_script_task=True, use_go_client=True))

  data['shards'][0]['state'] = 'TIMED_OUT'
  del data['shards'][0]['exit_code']

  big_output_dir = {'summary.json': json.dumps(data)}
  for i, shard_data in enumerate(
        api.test_utils.generate_simplified_json_results(4, True, True)):
    big_output_dir['%s/output.json' % i] = json.dumps(shard_data)
  # Will cause unicode decode error if tried to decode.
  big_output_dir['0/binary.png'] = '\x00\x00\x89'
  big_output_dir['0/invalid.txt'] = '\x00\x00\x89'
  # Large text file
  big_output_dir['0/big_text.txt'] = 'lots of text\n' * 2000
  yield (
      api.test('isolated_large_outdir') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.raw_io.output_dir(big_output_dir)) +
      api.properties(isolated_script_task=True))

  summary_data = {
    'shards': [
      {
        'state': 'COMPLETED',
        'internal_failure': False,
        'exit_code': '0',
      }
    ]
  }
  json_results = {
    'interrupted': False,
    'version': 3,
    'path_delimiter': '/',
    'seconds_since_epoch': 0,
    'tests': {},
    'num_failures_by_type': {},
    'links': {'custom_link': 'http://example.com'}
  }
  yield (
      api.test('isolated_script_with_custom_merge') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.raw_io.output_dir({'summary.json': json.dumps(summary_data)}),
          api.json.output(json_results) + api.swarming.summary(summary_data)) +
      api.properties(
          isolated_script_task=True,
          merge={
            'script': '//fake_custom_merge_script.py',
          }))

  yield (
      api.test('isolated_script_with_custom_trigger_script') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output('hash_for_win hello_world.isolated')) +
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.raw_io.output_dir({'summary.json': json.dumps(summary_data)}),
          api.json.output(json_results) + api.swarming.summary(summary_data)) +
      api.properties(
          isolated_script_task=True,
          trigger_script={
            'script': '//fake_custom_trigger_script.py',
            'args': ['foo', 'bar'],
          }) +
      api.post_process(post_process.Filter(
          '[trigger] hello_world on Windows-7-SP1'))
  )

  summary_data = {
    'shards': [
      None,
      {
        'state': 'COMPLETED',
        'internal_failure': False,
        'exit_code': '0',
      },
    ]
  }
  yield (
      api.test('gtest_with_null_shard') +
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output('hash_for_linux hello_world.isolated')) +
      api.step_data(
          'hello_world',
          api.raw_io.output_dir({'summary.json': json.dumps(summary_data)}),
          api.swarming.summary(summary_data) +
          api.test_utils.canned_gtest_output(False)) +
      api.properties(
          platforms=('linux',),
          show_shards_in_collect_step=True,
          gtest_task=True))
  yield (
      api.test('isolated_script_with_null_shard') +
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output('hash_for_linux hello_world.isolated')) +
      api.step_data(
          'hello_world',
          api.raw_io.output_dir({'summary.json': json.dumps(summary_data)}),
          api.swarming.summary(summary_data)) +
      api.properties(
          platforms=('linux',),
          show_shards_in_collect_step=True,
          isolated_script_task=True))

  summary_data_deduped = {
    'shards': [
      {
        'state': 'COMPLETED',
        'internal_failure': False,
        'exit_code': '0',
      },
      {
        'state': 'COMPLETED',
        'internal_failure': False,
        'exit_code': '0',
        'deduped_from': None,
      },
      {
        'state': 'COMPLETED',
        'internal_failure': False,
        'exit_code': '0',
        'deduped_from': 'deadbeef',
      },
    ]
  }
  yield (
      api.test('gtest_with_deduped_shard') +
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output('hash_for_linux hello_world.isolated')) +
      api.step_data(
          'hello_world',
          api.raw_io.output_dir(
              {'summary.json': json.dumps(summary_data_deduped)}),
          api.swarming.summary(summary_data_deduped) +
          api.test_utils.canned_gtest_output(False)) +
      api.properties(
          platforms=('linux',),
          show_shards_in_collect_step=True,
          gtest_task=True))
