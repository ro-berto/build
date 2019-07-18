# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'goma',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/raw_io',
]

from recipe_engine import post_process
import textwrap


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium_clang'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARD=api.properties.get('target_cros_board'))
  api.chromium.apply_config('goma_hermetic_fallback')
  api.chromium.apply_config('goma_high_parallel')
  api.chromium.apply_config('goma_localoutputcache')
  api.chromium.apply_config('goma_enable_global_file_stat_cache')
  api.chromium.apply_config('use_autoninja')

  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)

  api.chromium.c.compile_py.goma_max_active_fail_fallback_tasks = 1
  api.chromium.ensure_goma()
  api.chromium.compile(use_goma_module=True)


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(buildername='test_buildername') +
      api.properties(buildnumber='1') +
      api.properties(mastername='test_mastername') +
      api.path.exists(api.path['checkout'].join(
          'tools', 'clang', 'scripts', 'process_crashreports.py'))
  )

  yield (
      api.test('compile_fail') +
      api.properties(buildername='test_buildername') +
      api.properties(mastername='test_mastername') +
      api.step_data('compile', retcode=1) +
      api.path.exists(api.path['checkout'].join(
          'tools', 'clang', 'scripts', 'process_crashreports.py')) +
      api.post_process(post_process.MustRun, 'process clang crashes') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('codesearch') +
      api.properties(
          buildername='test_buildername',
          chromium_apply_config=['codesearch'])
  )

  yield (
      api.test('official_win_luci') +
      api.properties(
          target_platform='win',
          buildername='test_buildername',
          chromium_apply_config=['official']) +
      api.runtime(is_luci=True, is_experimental=False)
  )

  yield (
      api.test('official_linux_buildbot') +
      api.properties(
          target_platform='linux',
          buildername='test_buildername',
          chromium_apply_config=['official'])
  )

  yield (
      api.test('chromeos') +
      api.properties(
          buildername='test_buildername',
          target_platform='chromeos',
          target_cros_board='x86-generic')
  )

  yield (
      api.test('chromeos_official') +
      api.properties(
          buildername='test_buildername',
          target_platform='chromeos',
          target_cros_board='x86-generic',
          chromium_apply_config=['official']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('goma_canary') +
      api.properties(
          buildername='test_buildername',
          chromium_apply_config=['goma_canary'])
  )

  yield (
      api.test('goma_localoutputcache_small') +
      api.properties(
          buildername='test_buildername',
          chromium_apply_config=['goma_localoutputcache_small'])
  )

  yield (
      api.test('goma_custom_jobs_debug') +
      api.properties(buildername='test_buildername') +
      api.goma(jobs=500, debug=True) + api.runtime(
          is_luci=True, is_experimental=False)
  )

  yield (
      api.test('clang_tot') +
      api.properties(
          buildername='test_buildername',
          chromium_apply_config=['clang_tot']) +
      api.post_process(post_process.StepCommandContains, 'clang_revision',
                                                        ['--use-tot-clang']) +
      api.post_process(post_process.DropExpectation)
  )

  gomacc_path = ('/b/s/w/ir/cache/goma/client/gomacc '
        '../../third_party/llvm-build/Release+Asserts/bin/clang++ '
        'long string of commands\n'
  )

  yield (
      api.test('compile_failure_summary') +
      api.properties(buildername='test_buildername') +
      api.properties(mastername='test_mastername') +
      api.chromium.change_line_limit(50) +
      api.override_step_data('compile', api.raw_io.output(
          gomacc_path +
          textwrap.dedent("""
            [1/1] CXX a.o
            filename:row:col: error: error info
          """).strip(),
          name='failure_summary'), retcode=1) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.ResultReason,
          textwrap.dedent("""
            ```
            /b...
            [1/1] CXX a.o
            filename:row:col: error: error info
            ```
          """).strip()) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('compile_error_summary') +
      api.properties(buildername='test_buildername') +
      api.properties(mastername='test_mastername') +
      api.chromium.change_char_size_limit(150) +
      api.override_step_data('compile', api.raw_io.output(
          gomacc_path +
          textwrap.dedent("""
          [1/1] CXX a.o
          filename:row:col: error: error 1 info
          More stuff that happened in the error
          filename:row:col: error: error 2 info
          Actual code of where the error happened
          """),
          name='failure_summary'), retcode=1) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.ResultReason,
          textwrap.dedent("""\
          **Compile failure**

          List of errors:

          - ```filename:row:col: error: error 1 info```

          - ```filename:row:col: error: error 2 info```""")) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('compile_failure_long_summary') +
      api.properties(buildername='test_buildername') +
      api.properties(mastername='test_mastername') +
      api.chromium.change_char_size_limit(150) +
      api.override_step_data('compile', api.raw_io.output(
          gomacc_path +
          textwrap.dedent("""
          [1/1] CXX a.o
          filename:row:col: error: error 1 info
          More stuff that happened in the error
          filename:row:col: error: error 2 info
          Actual code of where the error happened
          filename:row:col: error: error 3 info
          filename:row:col: error: error 4 info
          More stuff that happened in the error
          filename:row:col: error: error 5 info
          filename:row:col: error: error 6 info
          """),
          name='failure_summary'), retcode=1) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.ResultReason,
          textwrap.dedent("""\
          **Compile failure**

          List of errors:

          - ```filename:row:col: error: error 1 info```

          - ```filename:row:col: error: error 2 info```

          - ```filename:row:col: error: error 3 info```

          - ```filename:row:col: error: error 4 info```

          - ```filename:row:col: error: error 5 info```

          - **...1 error(s) (6 total)...**""")) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('compile_failure_no_re_match') +
      api.properties(buildername='test_buildername') +
      api.properties(mastername='test_mastername') +
      api.override_step_data('compile', api.raw_io.output(
          gomacc_path +
          textwrap.dedent("""
          [1/1] CXX a.o
          filename error 1 info
          More stuff that happened in the error
          filename error 2 info
          Actual code of where the error happened
          filename error 3 info
          More stuff that happened in the error
          filename error 4 info
          """),
          name='failure_summary'), retcode=1) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.ResultReason,
          textwrap.dedent("""\
          No lines that look like "...error:..." found in the compile output.
          Refer to raw_io.output[failure_summary] for more information.""")) +
      api.post_process(post_process.DropExpectation)
  )
