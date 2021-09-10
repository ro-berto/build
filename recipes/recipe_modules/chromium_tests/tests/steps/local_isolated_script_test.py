# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/python',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'test_utils',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
  test_name = api.properties.get('test_name') or 'base_unittests'

  isolate_coverage_data = api.properties.get('isolate_coverage_data', False)

  enable_resultdb = api.resultdb.enabled
  resultdb = steps.ResultDB(
      enable=True, result_format='json') if enable_resultdb else None
  test_spec = steps.LocalIsolatedScriptTestSpec.create(
      test_name,
      override_compile_targets=api.properties.get('override_compile_targets'),
      isolate_coverage_data=isolate_coverage_data,
      resultdb=resultdb)

  test = test_spec.get_test()

  assert not test.runs_on_swarming

  test_repeat_count = api.properties.get('repeat_count')
  if test_repeat_count:
    test.test_options = steps.TestOptions(
        test_filter=api.properties.get('test_filter'),
        repeat_count=test_repeat_count,
        retry_limit=0,
        run_disabled=bool(test_repeat_count))

  raw_cmd = api.properties.get('raw_cmd') or []
  if raw_cmd:
    test.raw_cmd = list(raw_cmd)

  relative_cwd = api.properties.get('relative_cwd') or None
  if relative_cwd:
    test.relative_cwd = relative_cwd

  try:
    test.pre_run(api, '')
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'isolate_target: %r' % test.isolate_target,
        'uses_local_devices: %r' % test.uses_local_devices,
        'uses_isolate: %r' % test.uses_isolate,
    ]

    if api.properties.get('log_pass_fail_counts'):
      api.step.active_result.presentation.logs['details'] = [
        'pass_fail_counts: %r' % test.pass_fail_counts('')
      ]


def GenTests(api):
  def verify_log_fields(check, step_odict, expected_fields):
    """Verifies fields in details log are with expected values."""
    step = step_odict['details']
    for field in expected_fields.iteritems():
      expected_log = '%s: %r' % field
      check(expected_log in step.logs['details'])

  def verify_isolate_flag(check, step_odict):
    step = step_odict[
        'base_unittests']
    check(
        'LLVM_PROFILE_FILE=${ISOLATED_OUTDIR}/profraw/default-%1m.profraw'
        in step.cmd)

  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),
  )

  yield api.test(
      'raw_cmd',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          raw_cmd=['./base_unittests', '--bar'],
          relative_cwd='out/Release'),
      api.post_process(post_process.StepCommandContains, 'base_unittests', [
          '--relative-cwd', 'out/Release', '--', './base_unittests', '--bar',
          '--isolated-script-test-output'
      ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'override_compile_targets',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          override_compile_targets=['base_unittests_run']),
  )

  yield api.test(
      'log_pass_fail_counts',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          log_pass_fail_counts=True),
      api.post_process(verify_log_fields, {'pass_fail_counts': {}}),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'log_pass_fail_counts_invalid_results',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          log_pass_fail_counts=True),
      api.override_step_data(
          'base_unittests',
          api.test_utils.m.json.output({'interrupted': True}, 255)),
      api.post_process(verify_log_fields, {'pass_fail_counts': {}}),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'customized_test_options',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          swarm_hashes={
              'blink_web_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          test_filter=['test1', 'test2'],
          repeat_count=20,
          test_name='blink_web_tests'),
  )
  yield api.test(
      'isolate_coverage_data',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          isolate_coverage_data=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.post_process(verify_isolate_flag),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_resultdb_enabled',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),
      api.post_process(post_process.StepCommandContains, 'base_unittests',
                       ['rdb']),
      api.post_process(post_process.DropExpectation),
  )
