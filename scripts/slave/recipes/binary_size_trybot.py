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
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'filter',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'recipe_engine/time',
]

_ANALYZE_TARGETS = [
    '//chrome/android:monochrome_public_apk',
    '//tools/binary_size:binary_size_trybot_py',
]
_COMPILE_TARGETS = [
    'monochrome_public_apk',
    'monochrome_static_initializers',
]
_APK_NAME = 'MonochromePublic.apk'
_PATCH_FIXED_BUILD_STEP_NAME = (
    'Not measuring binary size because build is broken without patch.')
_FOOTER_PRESENT_STEP_NAME = (
    'Not measuring binary size because Binary-Size justification was provided.')
_NDJSON_GS_BUCKET = 'chromium-binary-size-trybot-results'
_HTML_REPORT_BASE_URL = (
    'https://storage.googleapis.com/chrome-supersize/viewer.html?load_url='
    'https://storage.googleapis.com/' + _NDJSON_GS_BUCKET + '/')

_TEST_TIME = 1454371200
_TEST_BUILDNUMBER = '200'
_TEST_TIME_FMT = '2016/02/02'


def RunSteps(api):
  assert api.tryserver.is_tryserver

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.gclient.apply_config('android')
    api.chromium.set_config('chromium')
    api.chromium.apply_config('mb')
    api.chromium_android.set_config('base_config')

    revision_info = api.gerrit.get_revision_info(
        api.properties['patch_gerrit_url'],
        api.properties['patch_issue'],
        api.properties['patch_set'])
    author = revision_info['commit']['author']['email']
    # get_footer returns a list of footer values.
    size_footers = api.tryserver.get_footer(
        'Binary-Size', patch_text=revision_info['commit']['message'])
    # Short-circuit early so that the bot is fast when disabled via header.
    # Although the bot is also meant to test compiles of official builds,
    # headers are generally only added when a previous job compiles fine and
    # fails with the "You need to add the header" message.
    if size_footers:
      api.python.succeeding_step(_FOOTER_PRESENT_STEP_NAME, '')
      return

    suffix = ' (with patch)'
    bot_config = {}
    checkout_dir = api.chromium_checkout.get_checkout_dir(bot_config)
    with api.context(cwd=checkout_dir):
      bot_update_step = api.chromium_checkout.ensure_checkout(bot_config)
    api.chromium.runhooks(name='runhooks' + suffix)

    affected_files = api.chromium_checkout.get_files_affected_by_patch()
    if not api.filter.analyze(affected_files, _ANALYZE_TARGETS, None,
                              'trybot_analyze_config.json')[0]:
      return

    api.chromium.ensure_goma()
    with_results_dir = _BuildAndMeasure(api, True)

    with api.context(cwd=api.chromium_checkout.working_dir):
      api.bot_update.deapply_patch(bot_update_step)

    with api.context(cwd=api.path['checkout']):
      suffix = ' (without patch)'
      try:
        api.chromium.runhooks(name='runhooks' + suffix)
        without_results_dir = _BuildAndMeasure(api, False)
      except api.step.StepFailure:
        api.python.succeeding_step(_PATCH_FIXED_BUILD_STEP_NAME, '')
        return

    # Re-apply patch so that the diff scripts can be tested via tryjobs.
    # We could build without-patch first to avoid having to apply the patch
    # twice, but it's nicer to fail fast when the patch does not compile.
    suffix = ' (with patch again)'
    with api.context(cwd=checkout_dir):
      bot_update_step = api.bot_update.ensure_checkout(suffix=suffix,
                                                       patch=True)
    api.chromium.runhooks(name='runhooks' + suffix)

    with api.context(cwd=api.path['checkout']):
      output_dir = api.chromium.output_dir
      resource_sizes_diff_path = output_dir.join('resource_sizes_diff.txt')
      dex_method_count_diff_path = output_dir.join('dex_method_counts_diff.txt')
      supersize_diff_path = output_dir.join('supersize_diff.txt')
      ndjson_path = output_dir.join('report.ndjson')
      results_path = output_dir.join('results.json')

      _CreateDiffs(api, author, without_results_dir, with_results_dir,
                   resource_sizes_diff_path, supersize_diff_path,
                   dex_method_count_diff_path, ndjson_path, results_path)

      _UploadNdJson(api, ndjson_path)

      _DisplayDiffResults(api, 'Resource Sizes', resource_sizes_diff_path,
                          '(Look here for high-level metrics)')
      _DisplayDiffResults(api, 'Supersize', supersize_diff_path,
                          '(Look here for detailed breakdown)')
      _DisplayDiffResults(api, 'Dex Method Count', dex_method_count_diff_path,
                          '(Look here for added/removed Java methods)')

      _CheckForUndocumentedIncrease(api, results_path)


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
      api.chromium_android.c.resource_sizes, [
          str(apk_path),
          '--chartjson',
          '--output-dir', results_dir,
          '--chromium-output-directory', api.chromium.output_dir,
      ])
  api.json.read(
      'resource_sizes result{}'.format(suffix),
      results_dir.join('results-chart.json'))

  size_path = results_dir.join(_APK_NAME + '.size')
  api.chromium_android.supersize_archive(
      apk_path, size_path, step_suffix=suffix)
  return results_dir


def _CheckForUndocumentedIncrease(api, results_path):
  step_result = api.json.read(
      'Check for undocumented increase', results_path,
      step_test_data=lambda: api.json.test_api.output({
          'details': 'Binary size checks passed.',
          'normalized_apk_size': 1024,
          'status_code': 0,
      }))
  result_json = step_result.json.output
  presentation = step_result.presentation

  try:
    presentation.logs['Size delta summary'] = (
        result_json['details'].splitlines())
    presentation.step_text = 'Normalized apk size delta: {} bytes'.format(
        result_json['normalized_apk_size'])
    if result_json['status_code'] != 0:
      presentation.status = api.step.FAILURE
      raise api.step.StepFailure('Undocumented size increase detected')
  except KeyError:
    presentation.status = api.step.FAILURE
    raise api.step.StepFailure('Malformed results JSON detected')


def _CreateDiffs(api, author, before_dir, after_dir, resource_sizes_diff_path,
                 supersize_diff_path, dex_method_count_diff_path,
                 ndjson_path, results_path):
  checker_script = api.path['checkout'].join(
      'tools', 'binary_size', 'trybot_commit_size_checker.py')

  api.python('Generate diffs', checker_script, [
      '--author', author,
      '--apk-name', _APK_NAME,
      '--before-dir', before_dir,
      '--after-dir', after_dir,
      '--resource-sizes-diff-path', resource_sizes_diff_path,
      '--supersize-diff-path', supersize_diff_path,
      '--dex-method-count-diff-path', dex_method_count_diff_path,
      '--ndjson-path', ndjson_path,
      "--results-path", results_path
  ])


def _DisplayDiffResults(api, name, path, description):
  diff_text = api.file.read_text('Show {} Diff'.format(name), path,
                                 test_data='Test output data')
  read_step_result = api.step.active_result
  read_step_result.presentation.step_text = description
  read_step_result.presentation.logs['>>> View {} Diff <<<'.format(name)] = (
      diff_text.splitlines())


def _UploadNdJson(api, ndjson_path):
  today = api.time.utcnow().date()
  gs_dest = '{}/{}/{}.ndjson'.format(
      api.buildbucket.builder_name,
      today.strftime('%Y/%m/%d'),
      api.buildbucket.build.number)
  upload_result = api.gsutil.upload(
      source=ndjson_path,
      bucket=_NDJSON_GS_BUCKET,
      dest=gs_dest,
      name='upload Supersize HTML report',
      link_name='Supersize HTML Report',
      unauthenticated_url=True)
  report_link_text = '>>> View Supersize HTML Report <<<'
  upload_result.presentation.links[report_link_text] = (
      _HTML_REPORT_BASE_URL + gs_dest)


def GenTests(api):
  def props(name, size_footer=False, **kwargs):
    kwargs.setdefault('path_config', 'kitchen')
    kwargs['revision'] = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    revision_info = {
        '_number': 1,
        'commit': {
            'author': {
                'email': 'foo@bar.com',
            },
            'message': 'message',
        }
    }
    footer_json = {}
    if size_footer:
      footer_json['Binary-Size'] = ['Totally worth it.']
    return (
        api.test(name) +
        api.properties.tryserver(
            build_config='Release',
            mastername='tryserver.chromium.android',
            buildername='android_binary_size',
            buildnumber=_TEST_BUILDNUMBER,
            patch_set=1,
            **kwargs) +
        api.platform('linux', 64) +
        api.override_step_data(
            'gerrit changes',
            api.json.output([{
                'revisions': {
                    kwargs['revision']: revision_info
                }
            }])) +
        api.override_step_data('parse description',
                               api.json.output(footer_json)) +
        api.time.seed(_TEST_TIME)
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
      props('noop_because_of_size_footer', size_footer=True) +
      api.post_process(post_process.MustRun, _FOOTER_PRESENT_STEP_NAME) +
      api.post_process(post_process.DropExpectation)
  )
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
      api.post_process(
          post_process.AnnotationContains,
          'gsutil upload Supersize HTML report',
          ['{}android_binary_size/{}/{}.ndjson'.format(
              _HTML_REPORT_BASE_URL, _TEST_TIME_FMT, _TEST_BUILDNUMBER)])
  )
  yield (
      props('unexpected_increase') +
      override_analyze() +
      api.override_step_data(
          'Check for undocumented increase',
          api.json.output({
            'details': 'Failed',
            'normalized_apk_size': 1024 * 17,
            'status_code': 1
          }))
  )
  yield(
      props('malformed_results_json') +
      override_analyze() +
      api.override_step_data(
          'Check for undocumented increase',
          api.json.output({
            'details': 'Failed',
            'normalized_apk_size': 1024 * 17,
            'error_code': 1
          }))
  )
