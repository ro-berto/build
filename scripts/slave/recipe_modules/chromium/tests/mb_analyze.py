# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'chromium_checkout',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/json',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.chromium_checkout.ensure_checkout({})
  with api.context(cwd=api.chromium_checkout.get_checkout_dir({})):
    api.chromium.mb_analyze(
        'test_mastername',
        'test_buildername',
        {
            'files': ['base/test/launcher/test_launcher.cc'],
            'test_targets': ['base_unittests'],
            'additional_compile_targets': ['chrome']
        })


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='test_mastername',
          buildername='test_buildername',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.post_process(post_process.MustRun, 'analyze') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('analyze_failure') +
      api.properties.tryserver(
          mastername='test_mastername',
          buildername='test_buildername',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.step_data('analyze',
          api.json.output({
            'output': 'ERROR at line 5: missing )'
          }, name="failure_summary"),
          retcode=1
      ) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.ResultReason,
          'ERROR at line 5: missing )') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('analyze_failure_no_output') +
      api.properties.tryserver(
          mastername='test_mastername',
          buildername='test_buildername',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.step_data('analyze',
          api.json.output({'output': ''}, name="failure_summary"),
          retcode=1
      ) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.ResultReason,
          "Step('analyze') (retcode: 1)") +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('analyze_failure_no_re') +
      api.properties.tryserver(
          mastername='test_mastername',
          buildername='test_buildername',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium.change_char_size_limit(5) +
      api.step_data('analyze',
          api.json.output({
            'output': 'line 5: missing )'
          }, name="failure_summary"),
          retcode=1
      ) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.ResultReason,
          ('No lines that look like "...ERROR at..." '
            'found in the compile output.\n'
            'Refer to stdout for more information.')) +
      api.post_process(post_process.DropExpectation)
  )
