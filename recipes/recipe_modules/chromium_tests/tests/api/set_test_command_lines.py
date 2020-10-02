# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

DEPS = [
    'build',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_results',
    'test_utils',
]


def RunSteps(api):
  if api.tryserver.is_tryserver:
    with api.chromium.chromium_layout():
      return api.chromium_tests.trybot_steps()
  else:
    with api.chromium.chromium_layout():
      return api.chromium_tests.main_waterfall_steps()


def GenTests(api):
  fake_group = 'fake-group'
  fake_builder = 'fake-builder'
  fake_tester = 'fake-tester'
  fake_try_builder = 'fake-try-builder'
  fake_test = 'fake_test'
  fake_source_side_spec = (fake_group, {
      fake_tester: {
          'isolated_scripts': [{
              'name': fake_test,
              'swarming': {
                  'can_use_on_swarming_builders': True,
              },
          }],
      }
  })
  fake_swarm_hashes = {fake_test: 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'}
  fake_command_lines_hash = 'ffffffffffffffffffffffffffffffff'
  fake_command_lines = {
      fake_test: [
          './%s' % fake_test, '--fake-flag', '--fake-log-file',
          '$ISOLATED_OUTDIR/fake.log'
      ],
  }

  def is_subsequence(containing, contained):
    result = False
    for i in range(len(containing) - len(contained) + 1):
      if containing[i:i + len(contained)] == contained:
        result = True
        break
    return result

  yield api.test(
      'combined_builder_tester',
      api.chromium.ci_build(builder_group=fake_group, builder=fake_tester),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.platform('linux', 64),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              fake_group: {
                  fake_tester:
                      bot_spec.BotSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          isolate_server='https://isolateserver.appspot.com',
                      ),
              },
          })),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.post_process(post_process.StepCommandContains,
                       'test_pre_run.[trigger] %s' % fake_test,
                       ['--env', 'ISOLATED_OUTDIR', '${ISOLATED_OUTDIR}']),
      api.post_process(post_process.StepCommandContains,
                       'test_pre_run.[trigger] %s' % fake_test,
                       ['--relative-cwd', 'out/Release', '--raw-cmd', '--'] +
                       fake_command_lines[fake_test]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'combined_builder_tester_use_swarming',
      api.chromium.ci_build(builder_group=fake_group, builder=fake_tester),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.platform('linux', 64),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              fake_group: {
                  fake_tester:
                      bot_spec.BotSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          isolate_server='https://isolateserver.appspot.com',
                          chromium_tests_apply_config=[
                              'use_swarming_recipe_to_trigger'
                          ],
                      ),
              },
          })),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.post_check(
          api.swarming.check_triggered_request,
          'test_pre_run.[trigger] %s' % fake_test, lambda check, req: check(req[
              0].relative_cwd == 'out/Release'), lambda check, req: check(
                  is_subsequence(req[0].command, fake_command_lines[fake_test])
              ), lambda check, req: check(req[0].env_vars['ISOLATED_OUTDIR'] ==
                                          '${ISOLATED_OUTDIR}')),
      api.post_process(post_process.DropExpectation),
  )

  fake_bot_db = bot_db.BotDatabase.create({
      fake_group: {
          fake_builder:
              bot_spec.BotSpec.create(
                  chromium_config='chromium', gclient_config='chromium'),
          fake_tester:
              bot_spec.BotSpec.create(
                  execution_mode=bot_spec.TEST,
                  parent_buildername=fake_builder,
                  chromium_config='chromium',
                  gclient_config='chromium',
                  build_gs_bucket='chromium-example-archive'),
      }
  })

  yield api.test(
      'build_only_builder_sets_command_line_hash_and_cwd_in_trigger',
      api.chromium.ci_build(builder_group=fake_group, builder=fake_builder),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.platform('linux', 64),
      api.chromium_tests.builders(fake_bot_db),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.step_data('archive command lines',
                    api.raw_io.output_text(fake_command_lines_hash)),
      api.post_process(post_process.LogContains, 'trigger', 'input',
                       [fake_command_lines_hash]),
      api.post_process(post_process.LogContains, 'trigger', 'input',
                       ['swarming_command_lines_cwd', 'out/Release']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'test_only_builder_gets_command_lines_hash_and_cwd_from_trigger',
      api.chromium.ci_build(builder_group=fake_group, builder=fake_tester),
      api.properties(
          swarm_hashes=fake_swarm_hashes,
          swarming_command_lines_hash=fake_command_lines_hash,
          swarming_command_lines_cwd='out/Release_x64'),
      api.platform('linux', 64),
      api.chromium_tests.builders(fake_bot_db),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.step_data('read command lines',
                    api.file.read_json(fake_command_lines)),
      api.post_process(
          post_process.StepCommandContains, 'test_pre_run.[trigger] fake_test',
          ['--relative-cwd', 'out/Release_x64', '--raw-cmd', '--'] +
          fake_command_lines[fake_test]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'test_only_builder_with_no_isolates',
      api.chromium.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          parent_buildername=fake_builder),
      api.platform('linux', 64),
      api.chromium_tests.builders(fake_bot_db),
      api.chromium_tests.read_source_side_spec(
          fake_group, {
              fake_tester: {
                  'gtest_tests': [{
                      'name': fake_test,
                      'swarming': {
                          'can_use_on_swarming_builders': False,
                      }
                  }],
              }
          }),
      api.post_process(post_process.DoesNotRun, 'read command lines'),
      api.post_process(post_process.MustRun, 'extract build'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'trybot_with_test_failure',
      api.chromium.try_build(
          builder_group=fake_group, builder=fake_try_builder),
      api.properties(
          config='Release',
          swarm_hashes=fake_swarm_hashes,
      ),
      api.platform('linux', 64),
      api.chromium_tests.trybots(
          try_spec.TryDatabase.create({
              fake_group: {
                  fake_try_builder:
                      try_spec.TrySpec.create(mirrors=[
                          try_spec.TryMirror.create(
                              builder_group=fake_group,
                              buildername=fake_builder,
                              tester=fake_tester,
                          )
                      ])
              }
          })),
      api.chromium_tests.builders(fake_bot_db),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
              'base': {
                  'exclusions': ['f.*'],
              },
              'chromium': {
                  'exclusions': [],
              }
          })),
      api.override_step_data(
          '%s (with patch)' % fake_test,
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  isolated_script_passing=False,
              ))),
      api.override_step_data(
          '%s (retry shards with patch)' % fake_test,
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  isolated_script_passing=False,
              ))),
      api.override_step_data(
          '%s (without patch)' % fake_test,
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  isolated_script_passing=True,
              ))),
      api.post_process(post_process.MustRun, 'find command lines (with patch)'),
      api.post_process(post_process.MustRun,
                       'find command lines (without patch)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      "ci_bot_with_experimental_test",
      api.chromium.ci_build(builder_group=fake_group, builder=fake_tester),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.platform('linux', 64),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              fake_group: {
                  fake_tester:
                      bot_spec.BotSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          isolate_server='https://isolateserver.appspot.com',
                      ),
              },
          })),
      api.chromium_tests.read_source_side_spec(
          fake_group, {
              fake_tester: {
                  'isolated_scripts': [{
                      'name': fake_test,
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'experiment_percentage': 100
                  }],
              }
          }),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.post_process(post_process.StepCommandContains,
                       'test_pre_run.[trigger] %s (experimental)' % fake_test,
                       ['--relative-cwd', 'out/Release', '--raw-cmd', '--'] +
                       fake_command_lines[fake_test]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      "ci_bot_with_experimental_test_use_swarming",
      api.chromium.ci_build(builder_group=fake_group, builder=fake_tester),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.platform('linux', 64),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              fake_group: {
                  fake_tester:
                      bot_spec.BotSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          isolate_server='https://isolateserver.appspot.com',
                          chromium_tests_apply_config=[
                              'use_swarming_recipe_to_trigger'
                          ],
                      ),
              },
          })),
      api.chromium_tests.read_source_side_spec(
          fake_group, {
              fake_tester: {
                  'isolated_scripts': [{
                      'name': fake_test,
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'experiment_percentage': 100
                  }],
              }
          }),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.post_process(
          api.swarming.check_triggered_request,
          'test_pre_run.[trigger] %s (experimental)' % fake_test, lambda check,
          req: check(req[0].relative_cwd == 'out/Release'), lambda check, req:
          check(is_subsequence(req[0].command, fake_command_lines[fake_test]))),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      "ci_bot_with_rdb_enabled_swarming_test",
      api.chromium.ci_build(builder_group=fake_group, builder=fake_tester),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.platform('linux', 64),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              fake_group: {
                  fake_tester:
                      bot_spec.BotSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          isolate_server='https://isolateserver.appspot.com',
                      ),
              },
          })),
      api.chromium_tests.read_source_side_spec(
          fake_group, {
              fake_tester: {
                  'isolated_scripts': [{
                      'name': fake_test,
                      'resultdb': {
                          'enable': True,
                          'test_location_base': '//test/location',
                      },
                      'swarming': {
                          'can_use_on_swarming_builders':
                              True,
                          'dimension_sets': [{
                              'device_type': 'phone',
                              'device_os': 'android',
                              'gpu': 'nv',
                              'os': 'Linux',
                          }],
                      },
                      'test_id_prefix': 'ninja://:fake_test/',
                  }],
              }
          }),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run.[trigger] %s on (nv) GPU on Linux' % fake_test, [
              '--relative-cwd', 'out/Release', '--raw-cmd', '--', 'rdb',
              'stream', '-test-id-prefix', 'ninja://:fake_test/', '-var',
              'builder:fake-tester', '-var', 'device_os:android', '-var',
              'device_type:phone', '-var', 'gpu:nv', '-var', 'os:Linux', '-var',
              'test_suite:fake_test', '-test-location-base', '//test/location',
              '-tag',
              'step_name:%s on (nv) GPU on Linux' % fake_test, '--'
          ] + fake_command_lines[fake_test]),
      api.post_process(post_process.DropExpectation),
  )
