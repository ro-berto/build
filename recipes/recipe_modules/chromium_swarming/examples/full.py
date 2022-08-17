# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from six.moves import range  # pylint: disable=redefined-builtin

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'code_coverage',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'swarming_client',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_swarming
from RECIPE_MODULES.build.chromium_tests.steps import ResultDB

PROPERTIES = {
    'platforms': Property(default=('win',)),
    'custom_trigger_script': Property(default=False),
    'show_outputs_ref_in_collect_step': Property(default=True),
    'gtest_task': Property(default=False),
    'isolated_script_task': Property(default=False),
    'merge': Property(default=None),
    'trigger_script': Property(default=None),
    'named_caches': Property(default=None),
    'service_account': Property(default=None),
    'wait_for_tasks': Property(default=None),
    'realm': Property(default=None),
    'resultdb_spec': Property(default={}),
}

def RunSteps(api, platforms, custom_trigger_script,
             show_outputs_ref_in_collect_step, gtest_task, isolated_script_task,
             merge, trigger_script, named_caches, service_account,
             wait_for_tasks, realm, resultdb_spec):
  # Checkout swarming client.
  api.swarming_client.checkout('master')

  api.gclient.set_config('chromium')
  api.chromium_checkout.ensure_checkout()

  # Configure swarming modules (this is optional).
  api.chromium_swarming.add_default_tag('builder_group:tryserver')
  api.chromium_swarming.default_expiration = 60*60
  api.chromium_swarming.default_hard_timeout = 60*60
  api.chromium_swarming.default_io_timeout = 20*60
  api.chromium_swarming.default_idempotent = True
  api.chromium_swarming.default_priority = 30
  api.chromium_swarming.default_user = 'joe'
  api.chromium_swarming.set_default_env('TESTING', '1')
  api.chromium_swarming.verbose = True
  api.chromium_swarming.task_output_stdout = 'json'

  api.chromium_swarming.set_default_dimension('inexistent', None)

  api.chromium_swarming.show_outputs_ref_in_collect_step = (
      show_outputs_ref_in_collect_step)

  try:
    # Testing ReadOnlyDict.__setattr__() coverage.
    api.chromium_swarming.default_dimensions['invalid'] = 'foo'
  except TypeError:
    pass
  try:
    api.chromium_swarming.default_env['invalid'] = 'foo'
  except TypeError:
    pass

  # Create a temp dir to put *.isolated files into.
  temp_dir = api.path.mkdtemp('hello_isolated_world')

  # Make sure the created Swarming requests all have `pool` in its dimension
  api.chromium_swarming.set_default_dimension('pool', 'foo')

  # Prepare a bunch of swarming tasks to run hello_world on multiple platforms.
  tasks = []
  resultdb = ResultDB.create(**resultdb_spec)
  for platform in platforms:
    # Isolate example hello_world.isolate from swarming client repo.
    # TODO(vadimsh): Add a thin wrapper around isolate to 'isolate' module?
    step_result = api.step(
        'archive for %s' % platform, [
            'tools/luci-go/isolate',
            'archive',
            '-isolate',
            api.swarming_client.path.join('example', 'payload',
                                          'hello_world.isolate'),
            '-verbose',
        ],
        stdout=api.raw_io.output_text())
    # TODO(vadimsh): Pass result from isolate though --output-json option.
    cas_input_root = step_result.stdout.split()[0].strip()

    # Create a task to run the isolated file on swarming, set OS dimension.
    # Also generate code coverage for multi-shard case by triggering multiple
    # shards on Linux.
    if gtest_task:
      task = api.chromium_swarming.gtest_task(
          raw_cmd=['hello_world.exe'],
          name='hello_world',
          cas_input_root=cas_input_root,
          task_output_dir=temp_dir.join('task_output_dir'),
          merge=merge)
    elif isolated_script_task:
      task = api.chromium_swarming.isolated_script_task()
      task_request = task.request
      task_slice = task_request[0]

      task_slice = (
          task_slice.with_cas_input_root(cas_input_root).with_env_vars(**{
              'IS_GTEST': '',
              'IS_SCRIPTTEST': 'True'
          }))
      task.request = (
          task_request.with_slice(0, task_slice).with_name('hello_world'))

      if realm:
        task.request = task.request.with_realm(realm)

      task.task_output_dir = temp_dir.join('task_output_dir')
      if merge:
        task.merge = merge
      task.trigger_script = trigger_script
    else:
      task = api.chromium_swarming.task(
          name='hello_world',
          cas_input_root=cas_input_root,
          extra_args=['--foo', '42'],
          task_output_dir=temp_dir.join('task_output_dir'),
          named_caches=named_caches,
          service_account=service_account,
          cipd_packages=[
              chromium_swarming.CipdPackage.create(
                  name='cool/package',
                  version='vers',
                  root='',
              )
          ])

    if platform == 'linux':
      task.shards = 2
      task.shard_indices = range(task.shards)
    elif platform == 'mac':
      task.shards = 3
      task.shard_indices = [1]
    else:
      task.shards = 1
      task.shard_indices = [0]
    if custom_trigger_script:
      task.trigger_script = chromium_swarming.TriggerScript.create(
          script=api.path['cache'].join('custom_trigger.py'))

    task_request = task.request
    task_slice = task_request[0]
    task_dimensions = task_slice.dimensions
    task_dimensions['os'] = api.chromium_swarming.prefered_os_dimension(
        platform)
    task.tags.add('os:' + platform)

    # test_suite is required, if resultdb is enabled.
    if resultdb.enable:
      task.tags.add('test_suite:chromium_test')
    ensure_file = task_slice.cipd_ensure_file
    ensure_file.add_package('super/awesome/pkg', 'git_revision:deadbeef', 'bin')
    task_slice = (task_slice.with_dimensions(**task_dimensions).
                    with_cipd_ensure_file(ensure_file))
    task.request = task_request.with_slice(0, task_slice)
    tasks.append(task)

  # Launch all tasks.
  for task in tasks:
    api.chromium_swarming.trigger_task(
        task,
        resultdb=resultdb)
    assert len(task.get_task_shard_output_dirs()) == len(task.shard_indices)

  # Recipe can do something useful here locally while tasks are
  # running on swarming.
  api.step('local step', ['echo', 'running something locally'])

  if wait_for_tasks:
    task_ids = [
        task.get_task_ids() for task in tasks
    ]

    api.chromium_swarming.wait_for_finished_task_set(task_ids)
    api.chromium_swarming.wait_for_finished_task_set(task_ids)
    return

  # Wait for all tasks to complete.
  for task in tasks:
    step_result = api.chromium_swarming.collect_task(task)

  api.chromium_swarming.report_stats()

  # Cleanup.
  api.file.rmtree('remove temp dir', temp_dir)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text(
              'hash_for_mac/size hello_world.isolated')),
      api.properties(platforms=('win', 'linux', 'mac')),
  )

  yield api.test(
      'custom_trigger_script',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text(
              'hash_for_mac/size hello_world.isolated')),
      api.properties(platforms=('mac',), custom_trigger_script=True),
      api.post_process(
          post_process.StepCommandContains,
          '[trigger (custom trigger script)] hello_world on Mac-10.13',
          ['--shard-index', '1']),
      api.post_process(
          post_process.StepCommandContains,
          '[trigger (custom trigger script)] hello_world on Mac-10.13',
          ['--shards', '3']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'default_trigger_script',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text('hash/size hello_world.isolated')),
      api.properties(platforms=('linux',), custom_trigger_script=False),
      api.post_check(
          api.swarming.check_triggered_request,
          '[trigger] hello_world', lambda check, req: check(req[0].env_vars[
              'GTEST_SHARD_INDEX'] == '0'), lambda check, req: check(req[
                  0].env_vars['GTEST_TOTAL_SHARDS'] == '2'), lambda check, req:
          check(req[0].command[-2:] == ['--foo', '42'])),
      api.post_check(
          api.swarming.check_triggered_request,
          '[trigger] hello_world (2)', lambda check, req: check(req[0].env_vars[
              'GTEST_SHARD_INDEX'] == '1'), lambda check, req: check(req[
                  0].env_vars['GTEST_TOTAL_SHARDS'] == '2'), lambda check, req:
          check(req[0].command[-2:] == ['--foo', '42'])),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'wait_for_tasks',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text(
              'hash_for_mac/size hello_world.isolated')),
      # This is probably how you'd use the test api; testing what happens if one
      # set of tasks finishes first. This example code doesn't care what is
      # returned, but calling code of this usually does.
      api.chromium_swarming.wait_for_finished_task_set([
          ([['110000', '110100']], 1),
          ([['100000'], ['130000']], 1),
      ]),
      api.properties(platforms=('win', 'linux', 'mac'), wait_for_tasks=True),
      api.post_process(
          post_process.Filter('wait for tasks', 'wait for tasks (2)')),
  )


  for exp in [True, False]:
    yield api.test(
        'basic_luci' + ('_experimental' if exp else ''),
        api.runtime(is_experimental=exp),
        api.step_data(
            'archive for win',
            stdout=api.raw_io.output_text(
                'hash_for_win/size hello_world.isolated')),
        api.step_data(
            'archive for linux',
            stdout=api.raw_io.output_text(
                'hash_for_linux/size hello_world.isolated')),
        api.step_data(
            'archive for mac',
            stdout=api.raw_io.output_text(
                'hash_for_mac/size hello_world.isolated')),
        api.properties(platforms=('win', 'linux', 'mac')),
    )

  yield api.test(
      'named_caches',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text(
              'hash_for_mac/size hello_world.isolated')),
      api.properties(
          platforms=('mac',),
          named_caches={
              'foo': 'cache/foo',
              'bar': 'cache/bar'
          }),
  )

  yield api.test(
      'service_account',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text(
              'hash_for_mac/size hello_world.isolated')),
      api.properties(
          platforms=(
              'win',
              'linux',
              'mac',
          ),
          service_account='test@example.com'),
  )

  yield api.test(
      'gerrit_trybot',
      api.buildbucket.try_build(
          project='chromium',
          builder='linux',
          build_number=1,
          git_repo='https://chromium.googlesource.com/chromium/src'),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
  )

  yield api.test(
      'show_outputs_ref_in_collect_step',
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.properties(show_outputs_ref_in_collect_step=False),
  )

  data = {
    'shards': [
      {
        '': '',
      }
    ]
  }

  yield api.test(
      'gtest_with_outputs_ref',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True))),
  )

  data = {
    'shards': [
      {
        'duration': 120.0,
        'state': 'COMPLETED',
      }
    ]
  }

  yield api.test(
      'gtest_with_duration',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.chromium_swarming.summary(
              api.test_utils.canned_gtest_output(True), data)),
  )

  data = api.chromium_swarming.canned_summary_output_raw(shards=4)
  data['shards'][2]['completed_ts'] = '2014-09-25T01:49:23.123'
  data['shards'][3]['completed_ts'] = '2014-09-25T01:48:22.345'

  yield api.test(
      'gtest_with_long_task',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.chromium_swarming.summary(
              api.test_utils.canned_gtest_output(True), data)),
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
  yield api.test(
      'swarming_expired_new',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data('hello_world on Windows-7-SP1',
                    api.chromium_swarming.summary(None, data)),
  )
  yield api.test(
      'isolated_script_expired_new',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.raw_io.output_dir(
              {'summary.json': api.json.dumps(data).encode('utf-8')})),
      api.properties(isolated_script_task=True),
  )

  data['shards'][0]['state'] = 'TIMED_OUT'
  yield api.test(
      'swarming_timeout_new',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data('hello_world on Windows-7-SP1',
                    api.chromium_swarming.summary(None, data)),
  )
  yield api.test(
      'isolated_script_timeout_new',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.raw_io.output_dir(
              {'summary.json': api.json.dumps(data).encode('utf-8')})),
      api.properties(isolated_script_task=True),
  )

  data['shards'][0]['state'] = 'COMPLETED'
  data['shards'][0]['exit_code'] = '1'
  yield api.test(
      'isolated_script_non_zero_exit_status',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.chromium_swarming.summary(
              api.raw_io.output_dir(
                  {'summary.json': api.json.dumps(data).encode('utf-8')}),
              data)),
      api.properties(isolated_script_task=True),
  )

  data['shards'][0]['state'] = 'TIMED_OUT'
  del data['shards'][0]['exit_code']

  big_output_dir = {'summary.json': api.json.dumps(data).encode('utf-8')}
  for i, shard_data in enumerate(
        api.test_utils.generate_simplified_json_results(range(4), True, True)):
    big_output_dir['%s/output.json' % i] = (
        api.json.dumps(shard_data).encode('utf-8'))
  # Will cause unicode decode error if tried to decode.
  big_output_dir['0/binary.png'] = b'\x00\x00\x89'
  big_output_dir['0/invalid.txt'] = b'\x00\x00\x89'
  # Large text file
  big_output_dir['0/big_text.txt'] = b'lots of text\n' * 2000
  yield api.test(
      'isolated_large_outdir',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data('hello_world on Windows-7-SP1',
                    api.raw_io.output_dir(big_output_dir)),
      api.properties(isolated_script_task=True),
  )

  summary_data = {
    'shards': [
      {
        'state': 'COMPLETED',
        'internal_failure': False,
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
  yield api.test(
      'isolated_script_with_custom_merge',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.chromium_swarming.summary(
              api.raw_io.output_dir({
                  'summary.json': api.json.dumps(summary_data).encode('utf-8')
              }) + api.json.output(json_results), summary_data)),
      api.properties(
          isolated_script_task=True,
          merge=chromium_swarming.MergeScript.create(
              script=api.path['cache'].join('fake_custom_merge_script.py'))),
  )

  yield api.test(
      'isolated_script_with_custom_trigger_script',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'hello_world on Windows-7-SP1',
          api.chromium_swarming.summary(
              api.raw_io.output_dir({
                  'summary.json': api.json.dumps(summary_data).encode('utf-8')
              }) + api.json.output(json_results), summary_data)),
      api.properties(
          isolated_script_task=True,
          trigger_script=chromium_swarming.TriggerScript.create(
              script=api.path['cache'].join('fake_custom_trigger_script.py'),
              args=['foo', 'bar'],
          )),
      api.post_process(
          post_process.Filter(
              '[trigger (custom trigger script)] hello_world on Windows-7-SP1')
      ),
  )

  yield api.test(
      'isolated_script_with_realm',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text(
              'hash_for_mac/size hello_world.isolated')),
      api.properties(
          platforms=('win', 'linux', 'mac'),
          realm="test:task_realm",
          isolated_script_task=True),
  )

  yield api.test(
      'isolated_script_with_realm_and_resultdb',
      api.buildbucket.try_build(
          project='chromium', builder='linux', build_number=1),
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output_text(
              'hash_for_win/size hello_world.isolated')),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output_text(
              'hash_for_mac/size hello_world.isolated')),
      api.properties(
          platforms=('win', 'linux', 'mac'),
          isolated_script_task=True,
          realm="test:task_realm",
          resultdb_spec={'enable': True}),
  )

  summary_data = {
    'shards': [
      None,
      {
        'state': 'COMPLETED',
        'internal_failure': False,
      },
    ]
  }
  yield api.test(
      'gtest_with_null_shard',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'hello_world',
          api.chromium_swarming.summary(
              api.raw_io.output_dir({
                  'summary.json': api.json.dumps(summary_data).encode('utf-8')
              }) + api.test_utils.canned_gtest_output(False), summary_data)),
      api.properties(platforms=('linux',), gtest_task=True),
  )
  yield api.test(
      'isolated_script_with_null_shard',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'hello_world',
          api.chromium_swarming.summary(
              api.raw_io.output_dir({
                  'summary.json': api.json.dumps(summary_data).encode('utf-8')
              }), summary_data)),
      api.properties(platforms=('linux',), isolated_script_task=True),
  )
  yield api.test(
      'coverage_gtest_with_null_shard',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ), api.m.code_coverage(use_clang_coverage=True),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'hello_world',
          api.chromium_swarming.summary(
              api.raw_io.output_dir({
                  'summary.json': api.json.dumps(summary_data).encode('utf-8')
              }) + api.test_utils.canned_gtest_output(False), summary_data)),
      api.properties(platforms=('linux',), gtest_task=True),
      api.post_process(post_process.StepFailure, 'hello_world'),
      api.post_process(post_process.DropExpectation))

  summary_data_deduped = {
    'shards': [
      {
        'state': 'COMPLETED',
        'internal_failure': False,
      },
      {
        'state': 'COMPLETED',
        'internal_failure': False,
        'deduped_from': None,
      },
      {
        'state': 'COMPLETED',
        'internal_failure': False,
        'deduped_from': 'deadbeef',
      },
    ]
  }

  yield api.test(
      'gtest_with_deduped_shard',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'hello_world',
          api.chromium_swarming.summary(
              api.raw_io.output_dir({
                  'summary.json':
                      api.json.dumps(summary_data_deduped).encode('utf-8')
              }) + api.test_utils.canned_gtest_output(False),
              summary_data_deduped)),
      api.properties(platforms=('linux',), gtest_task=True),
  )

  missing_duration_data = api.chromium_swarming.canned_summary_output_raw()
  del missing_duration_data['shards'][0]['duration']
  yield api.test(
      'missing_duration',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output_text(
              'hash_for_linux/size hello_world.isolated')),
      api.step_data(
          'hello_world',
          api.chromium_swarming.summary(
              api.test_utils.canned_gtest_output(True), missing_duration_data)),
      api.properties(platforms=('linux',), gtest_task=True),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
