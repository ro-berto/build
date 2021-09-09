# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'build',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'depot_tools/bot_update',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/file',
    'recipe_engine/json',
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
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  if api.tryserver.is_tryserver:
    with api.chromium.chromium_layout():
      return api.chromium_tests.trybot_steps(builder_id, builder_config)
  else:
    with api.chromium.chromium_layout():
      return api.chromium_tests.main_waterfall_steps(builder_id, builder_config)


def GenTests(api):
  fake_group = 'fake-group'
  fake_builder = 'fake-builder'
  fake_tester = 'fake-tester'
  fake_try_builder = 'fake-try-builder'
  fake_test = 'fake_test'
  webgl_fake_test = 'webgl_fake_test'
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
  fake_swarm_hashes = {
      fake_test: 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
      webgl_fake_test: 'gggggggggggggggggggggggggg'
  }
  fake_command_lines_digest = (
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855/0')
  fake_command_lines = {
      fake_test: [
          './%s' % fake_test, '--fake-flag', '--fake-log-file',
          '$ISOLATED_OUTDIR/fake.log'
      ],
      webgl_fake_test: [
          './%s' % webgl_fake_test, '--fake-flag', '--fake-log-file',
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
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          builder_db=ctbc.BuilderDatabase.create({
              fake_group: {
                  fake_tester:
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.post_process(
          api.swarming.check_triggered_request, 'test_pre_run.[trigger] %s' %
          fake_test, lambda check, req: check(req[0].env_vars[
              'ISOLATED_OUTDIR'] == '${ISOLATED_OUTDIR}'), lambda check, req:
          check(req[0].relative_cwd == 'out/Release'), lambda check, req: check(
              is_subsequence(req[0].command, fake_command_lines[fake_test]))),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'combined_builder_tester_use_swarming',
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          builder_db=ctbc.BuilderDatabase.create({
              fake_group: {
                  fake_tester:
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.properties(swarm_hashes=fake_swarm_hashes),
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

  yield api.test(
      'combined_builder_tester_use_swarming_go_in_trigger_script',
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          builder_db=ctbc.BuilderDatabase.create({
              fake_group: {
                  fake_tester:
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.post_process(post_process.DropExpectation),
  )

  fake_builder_db = ctbc.BuilderDatabase.create({
      fake_group: {
          fake_builder:
              ctbc.BuilderSpec.create(
                  chromium_config='chromium', gclient_config='chromium'),
          fake_tester:
              ctbc.BuilderSpec.create(
                  execution_mode=ctbc.TEST,
                  parent_buildername=fake_builder,
                  chromium_config='chromium',
                  gclient_config='chromium',
                  build_gs_bucket='chromium-example-archive'),
      }
  })

  yield api.test(
      'build_only_builder_sets_command_line_hash_and_cwd_in_trigger',
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_builder,
          builder_db=fake_builder_db),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.step_data('archive command lines to RBE-CAS',
                    api.raw_io.output_text(fake_command_lines_digest)),
      api.post_process(post_process.LogContains, 'trigger', 'input',
                       [fake_command_lines_digest]),
      api.post_process(post_process.LogContains, 'trigger', 'input',
                       ['swarming_command_lines_cwd', 'out/Release']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'test_only_builder_gets_command_lines_hash_and_cwd_from_trigger',
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          builder_db=fake_builder_db),
      api.properties(
          swarm_hashes=fake_swarm_hashes,
          swarming_command_lines_digest=fake_command_lines_digest,
          swarming_command_lines_cwd='out/Release_x64'),
      api.chromium_tests.read_source_side_spec(*fake_source_side_spec),
      api.step_data('read command lines',
                    api.file.read_json(fake_command_lines)),
      api.post_process(
          api.swarming.check_triggered_request,
          'test_pre_run.[trigger] fake_test', lambda check, req: check(req[
              0].relative_cwd == 'out/Release_x64'), lambda check, req:
          check(is_subsequence(req[0].command, fake_command_lines[fake_test]))),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'test_only_builder_with_no_isolates',
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          parent_buildername=fake_builder,
          builder_db=fake_builder_db),
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
      api.chromium_tests_builder_config.try_build(
          builder_group=fake_group,
          builder=fake_try_builder,
          builder_db=fake_builder_db,
          try_db=ctbc.TryDatabase.create({
              fake_group: {
                  fake_try_builder:
                      ctbc.TrySpec.create(mirrors=[
                          ctbc.TryMirror.create(
                              builder_group=fake_group,
                              buildername=fake_builder,
                              tester=fake_tester,
                          )
                      ])
              }
          })),
      api.properties(
          config='Release',
          swarm_hashes=fake_swarm_hashes,
      ),
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
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          builder_db=ctbc.BuilderDatabase.create({
              fake_group: {
                  fake_tester:
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.properties(swarm_hashes=fake_swarm_hashes),
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
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          builder_db=ctbc.BuilderDatabase.create({
              fake_group: {
                  fake_tester:
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.chromium_tests.read_source_side_spec(
          fake_group, {
              fake_tester: {
                  'isolated_scripts': [{
                      'name': fake_test,
                      'resultdb': {
                          'enable': True,
                          'has_native_resultdb_integration': True,
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
          api.swarming.check_triggered_request,
          'test_pre_run.[trigger] %s on (nv) GPU on Linux' %
          fake_test, lambda check, req: check(req[
              0].relative_cwd == 'out/Release'), lambda check, req: check(
                  is_subsequence(req[0].command, [
                      'rdb',
                      'stream',
                      '-test-id-prefix',
                      'ninja://:fake_test/',
                      '-var',
                      'builder:fake-tester',
                      '-var',
                      'device_os:android',
                      '-var',
                      'device_type:phone',
                      '-var',
                      'gpu:nv',
                      '-var',
                      'os:Linux',
                      '-var',
                      'test_suite:fake_test',
                      '-test-location-base',
                      '//test/location',
                      '-tag',
                      'step_name:%s on (nv) GPU on Linux' % fake_test,
                      '-coerce-negative-duration',
                      '-location-tags-file',
                      '../../testing/location_tags.json',
                      '-exonerate-unexpected-pass',
                      '--',
                  ] + fake_command_lines[fake_test]))),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      "ci_bot_with_default_resultdb_swarming_gtest",
      api.chromium_tests_builder_config.ci_build(
          builder_group=fake_group,
          builder=fake_tester,
          builder_db=ctbc.BuilderDatabase.create({
              fake_group: {
                  fake_tester:
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.properties(swarm_hashes=fake_swarm_hashes),
      api.chromium_tests.read_source_side_spec(
          fake_group, {
              fake_tester: {
                  'gtest_tests': [{
                      'name': fake_test,
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'test_id_prefix': 'ninja://:fake_test/',
                  }],
              }
          }),
      api.step_data('find command lines', api.json.output(fake_command_lines)),
      api.post_process(
          api.swarming.check_triggered_request,
          'test_pre_run.[trigger] %s' % fake_test, lambda check, req: check(req[
              0].relative_cwd == 'out/Release'), lambda check, req: check(
                  is_subsequence(req[0].command, [
                      'rdb', 'stream', '-test-id-prefix', 'ninja://:fake_test/',
                      '-var', 'builder:fake-tester', '-var', 'os:Ubuntu-16.04',
                      '-var', 'test_suite:fake_test', '-tag',
                      'step_name:%s' % fake_test, '-coerce-negative-duration',
                      '-location-tags-file', '../../testing/location_tags.json',
                      '-exonerate-unexpected-pass', '--', 'result_adapter',
                      'gtest', '-result-file', '${ISOLATED_OUTDIR}/output.json',
                      '-artifact-directory', '${ISOLATED_OUTDIR}', '--'
                  ] + fake_command_lines[fake_test]))),
      api.post_process(post_process.DropExpectation),
  )
