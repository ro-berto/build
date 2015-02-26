# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'chromium_tests',
  'filter',
  'json',
  'properties',
  'tryserver',
]


def GenSteps(api):
  api.chromium.set_config('chromium')
  api.bot_update.ensure_checkout(force=True)

  exes = list(api.m.properties.get('exes', []))
  compile_targets = list(api.m.properties.get('compile_targets', []))

  out_result, out_exes, out_compile_targets = api.chromium_tests.analyze(
      api.tryserver.get_files_affected_by_patch(),
      exes, compile_targets, 'foo.json')

  if 'all' in compile_targets:
    # If "all" is included in the compile targets, all targets that depend
    # on the change and all matching exes are expected to be returned by
    # api.chromium_tests.analyze.
    assert sorted(out_compile_targets) == sorted(
        set(api.filter.matching_exes) | set(api.filter.compile_targets))
  else:
    # If "all" is not included in the compile targets, the targets in
    # |compiled_targets| that depend on the change and all matching exes are
    # expected to be returned by api.chromium_tests.analyze.
    assert sorted(out_compile_targets) == sorted(
        set(api.filter.matching_exes) | (set(compile_targets) &
                                         set(api.filter.compile_targets)))

def GenTests(api):
  yield (
    api.test('basic') +
    api.properties.tryserver() +
    api.properties(
      exes=['base_unittests'],
      compile_targets=['all']) +
    api.override_step_data('read filter exclusion spec', api.json.output({
        'base': {
          'exclusions': ['f.*'],
        },
        'chromium': {
          'exclusions': [],
        },
     })
    )
  )

  # Tests analyze with compile targets that do not include "all".
  yield (api.test('analyze_matches_compile_targets') +
         api.properties.tryserver() +
         api.properties(
           exes=['exe0', 'exe1'],
           compile_targets=['target0', 'target1']) +
         api.override_step_data(
          'analyze',
          api.json.output(
              {'status': 'Found dependency',
               'targets': ['exe0'],
               'build_targets': ['target0', 'target1', 'target2']})))

  # Tests analyze with compile targets that include "all".
  yield (api.test('analyze_matches_compile_targets_with_all') +
         api.properties.tryserver() +
         api.properties(
           exes=['exe0', 'exe1'],
           compile_targets=['all', 'target0', 'target1']) +
         api.override_step_data(
          'analyze',
          api.json.output(
              {'status': 'Found dependency',
               'targets': ['exe0'],
               'build_targets': ['target0', 'target1', 'target2']})))
