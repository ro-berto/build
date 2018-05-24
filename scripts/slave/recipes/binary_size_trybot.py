# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'chromium_android',
  'chromium_checkout',
  'chromium_tests',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gerrit',
  'depot_tools/tryserver',
  'filter',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

_ANALYZE_TARGETS = [
    '//chrome/android:monochrome_public_apk',
    '//tools/binary_size:binary_size_trybot_py',
]
_COMPILE_TARGETS = [
    'monochrome_public_apk',
]
_APK_NAME = 'MonochromePublic.apk'
_PATCH_FIXED_BUILD_STEP_NAME = (
    'Not measuring binary size because build is broken without patch.')


def RunSteps(api):
  assert api.tryserver.is_tryserver

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.gclient.apply_config('android')
    api.chromium.set_config('chromium')
    api.chromium.apply_config('mb')
    api.chromium_android.set_config('base_config')
    api.chromium.ensure_goma()

    suffix = ' (with patch)'
    bot_update_step = api.bot_update.ensure_checkout(suffix=suffix, patch=True)
    api.chromium.runhooks(name='runhooks' + suffix)

    affected_files = api.chromium_checkout.get_files_affected_by_patch()
    if not api.filter.analyze(affected_files, _ANALYZE_TARGETS, None,
                              'trybot_analyze_config.json')[0]:
      return

    with_results_dir = _BuildAndMeasure(api, True)

    with api.context(cwd=api.chromium_checkout.working_dir):
      api.bot_update.deapply_patch(bot_update_step)

    with api.context(cwd=api.path['checkout']):
      suffix = ' (without patch)'
      try:
        api.chromium.runhooks(name='runhooks' + suffix)
        without_results_dir = _BuildAndMeasure(api, False)
      except api.step.StepFailure:
        api.python.succeeding_step(_PATCH_FIXED_BUILD_STEP_NAME,
                                   _PATCH_FIXED_BUILD_STEP_NAME)
        return

      resource_sizes_diff_path = _ResourceSizesDiff(
          api, without_results_dir, with_results_dir)
      _SupersizeDiff(api, without_results_dir, with_results_dir)
      _CheckForUnexpectedIncrease(api, resource_sizes_diff_path)


def _BuildAndMeasure(api, with_patch):
  suffix = ' (with patch)' if with_patch else ' (without patch)'
  results_basename = 'with_patch' if with_patch else 'without_patch'

  api.chromium_tests.run_mb_and_compile(_COMPILE_TARGETS, None, suffix)

  results_dir = api.chromium.output_dir.join(results_basename)
  api.file.ensure_directory('mkdir ' + results_basename, results_dir)

  apk_path = api.chromium_android.apk_path(_APK_NAME)
  # Can't use api.chromium_android.resource_sizes() without it trying to upload
  # the results.
  api.python(
      'resource_sizes ({}){}'.format(api.path.basename(apk_path), suffix),
      api.chromium_android.c.resource_sizes,
      [str(apk_path), '--chartjson'])
  api.file.move('mv results-chart.json' + suffix, api.chromium.output_dir.join(
      'results-chart.json'), results_dir.join('results-chart.json'))

  size_path = results_dir.join(_APK_NAME + '.size')
  api.chromium_android.supersize_archive(
      apk_path, size_path, step_suffix=suffix)
  return results_dir


def _SupersizeDiff(api, without_results_dir, with_results_dir):
  diagnose_bloat = api.path['checkout'].join(
      'tools', 'binary_size', 'diagnose_bloat.py')
  diff_output_path = api.chromium.output_dir.join('supersize_diff.txt')
  api.python('Supersize diff', diagnose_bloat, [
      'diff',
      '--apk-name', _APK_NAME,
      '--diff-type', 'native',
      '--before-dir', without_results_dir,
      '--after-dir', with_results_dir,
      '--diff-output', diff_output_path,
  ])
  diff_text = api.file.read_text('Show Supersize Diff', diff_output_path)
  api.step.active_result.presentation.logs['diff'] = diff_text


def _ResourceSizesDiff(api, without_results_dir, with_results_dir):
  diagnose_bloat = api.path['checkout'].join(
      'tools', 'binary_size', 'diagnose_bloat.py')
  diff_output_path = api.chromium.output_dir.join('resource_sizes_diff.txt')
  api.python('resource_sizes diff', diagnose_bloat, [
      'diff',
      '--apk-name', _APK_NAME,
      '--diff-type', 'sizes',
      '--before-dir', without_results_dir,
      '--after-dir', with_results_dir,
      '--diff-output', diff_output_path,
  ])
  diff_text = api.file.read_text('Show Resource Sizes Diff', diff_output_path)
  api.step.active_result.presentation.logs['diff'] = diff_text
  return diff_output_path


def _CheckForUnexpectedIncrease(api, resource_sizes_diff_path):
  revision_info = api.gerrit.get_revision_info(
      api.properties['patch_gerrit_url'],
      api.properties['patch_issue'],
      api.properties['patch_set'])
  author = revision_info['commit']['author']['email']
  size_footer = ''.join(
      api.tryserver.get_footer('Binary-Size',
                               patch_text=revision_info['commit']['message']))
  checker_script = api.path['checkout'].join(
      'tools', 'binary_size', 'trybot_commit_size_checker.py')
  api.python('check for undocumented increase', checker_script, [
      '--author', author,
      '--size-footer', size_footer,
      '--resource-sizes-diff', resource_sizes_diff_path,
  ])


def GenTests(api):
  _REVISION = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
  def props(name, **kwargs):
    kwargs.setdefault('path_config', 'kitchen')
    kwargs['revision'] = _REVISION
    return (
        api.test(name) +
        api.properties.tryserver(
            build_config='Release',
            mastername='tryserver.chromium.android',
            buildername='android_binary_size',
            patch_set=1,
            **kwargs) +
        api.platform('linux', 64)
    )

  def override_revision_info():
    _REVISION_INFO = {
        '_number': 1,
        'commit': {
            'author': {
                'email': 'foo@bar.com',
            },
            'message': 'message',
        }
    }
    return (
        api.override_step_data(
            'gerrit changes',
            api.json.output([{
                'revisions': {
                    _REVISION: _REVISION_INFO
                }
            }])) +
        api.override_step_data('parse description', api.json.output({}))
    )


  def override_analyze(no_changes=False):
    """Overrides analyze step data so that targets get compiled."""
    return api.override_step_data(
        'analyze',
        api.json.output({
            'status': 'Found dependency',
            'compile_targets': _ANALYZE_TARGETS,
            'test_targets': [] if no_changes else _COMPILE_TARGETS}))

  yield (
      props('noop_because_of_analyze') +
      override_analyze(no_changes=True) +
      api.post_process(post_process.MustRun, 'analyze') +
      api.post_process(post_process.DoesNotRunRE, r'.*build') +
      api.post_process(post_process.DropExpectation)
  )
  yield (
      props('patch_fixes_build') +
      override_analyze() +
      api.override_step_data('compile (without patch)', retcode=1) +
      api.post_process(post_process.MustRun, _PATCH_FIXED_BUILD_STEP_NAME) +
      api.post_process(post_process.DropExpectation)
  )
  yield (
      props('normal_build') +
      override_analyze() +
      override_revision_info()
  )
