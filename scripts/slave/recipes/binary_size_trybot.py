# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine import recipe_api

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

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

_DEFAULT_ANALYZE_TARGETS = [
    '//chrome/android:monochrome_public_minimal_apks',
    '//tools/binary_size:binary_size_trybot_py',
]
_DEFAULT_COMPILE_TARGETS = [
    'monochrome_public_minimal_apks',
    'monochrome_static_initializers',
]
_DEFAULT_APK_NAME = 'MonochromePublic.minimal.apks'

_EXPECTATIONS_STEP_NAME = 'Checking for expectation failures'
_BUILD_VARS_PATH = 'build_vars.txt'

_PATCH_FIXED_BUILD_STEP_NAME = (
    'Not measuring binary size because build is broken without patch.')
_NDJSON_GS_BUCKET = 'chromium-binary-size-trybot-results'
_ARCHIVED_URL_PREFIX = (
    'https://storage.googleapis.com/' + _NDJSON_GS_BUCKET + '/')
_RESULT_JSON_STEP_NAME = 'Read diff results'
_RESULTS_STEP_NAME = 'Trybot Results'
_PLUGIN_OUTPUT_PROPERTY_NAME = 'binary_size_plugin'

_TEST_TIME = 1454371200
_TEST_BUILDER = 'android_binary_size'
_TEST_BUILDNUMBER = '200'
_TEST_TIME_FMT = '2016/02/02'


PROPERTIES = {
    'analyze_targets': recipe_api.Property(
        kind=list, default=_DEFAULT_ANALYZE_TARGETS,
        help='Fully-qualified GN targets to analyze.'),
    'compile_targets': recipe_api.Property(
        kind=list, default=_DEFAULT_COMPILE_TARGETS,
        help='Unqualified targets to compile.'),
    'apk_name': recipe_api.Property(
        kind=str, default=_DEFAULT_APK_NAME,
        help='Filename of the built apk or .minimal.apks to measure'),
}


def RunSteps(api, analyze_targets, compile_targets, apk_name):
  assert api.tryserver.is_tryserver

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.gclient.apply_config('android')
    api.chromium.set_config('chromium')
    api.chromium.apply_config('mb')
    api.chromium_android.set_config('base_config')

    revision_info = api.gerrit.get_revision_info(
        'https://%s' % api.tryserver.gerrit_change.host,
        api.tryserver.gerrit_change.change,
        api.tryserver.gerrit_change.patchset)
    author = revision_info['commit']['author']['email']
    commit_message = revision_info['commit']['message']
    is_revert = commit_message.startswith('Revert')
    # get_footer returns a list of footer values.
    has_size_footer = bool(api.tryserver.get_footer('Binary-Size',
                                                    patch_text=commit_message))
    allow_regressions = is_revert or has_size_footer

    suffix = ' (with patch)'
    bot_config = {}
    checkout_dir = api.chromium_checkout.get_checkout_dir(bot_config)
    with api.context(cwd=checkout_dir):
      bot_update_step = api.chromium_checkout.ensure_checkout(bot_config)
    api.chromium.runhooks(name='runhooks' + suffix)

    with api.context(cwd=api.chromium.output_dir):
      _ClearFailedExpectationFiles(api)

    affected_files = api.chromium_checkout.get_files_affected_by_patch()
    if not api.filter.analyze(affected_files, analyze_targets, None,
                              'trybot_analyze_config.json')[0]:
      step_result = api.step.active_result
      step_result.presentation.properties[_PLUGIN_OUTPUT_PROPERTY_NAME] = {
          'listings': [],
          'extras': [],
      }
      return

    api.chromium.ensure_goma()
    staging_dir = api.path.mkdtemp('binary-size-trybot')
    with_results_dir, raw_result = _BuildAndMeasure(
        api, True, compile_targets, apk_name, staging_dir)

    if raw_result and raw_result.status != common_pb.SUCCESS:
      return raw_result

    with api.context(cwd=api.chromium.output_dir):
      expectations_result_path = staging_dir.join('expectations_result.json')
      expectations_json = _CheckForFailedExpectationFiles(
        api, expectations_result_path)

    with api.context(cwd=api.chromium_checkout.working_dir):
      api.bot_update.deapply_patch(bot_update_step)

    with api.context(cwd=api.path['checkout']):
      suffix = ' (without patch)'

      api.chromium.runhooks(name='runhooks' + suffix)
      without_results_dir, raw_result = _BuildAndMeasure(
          api, False, compile_targets, apk_name, staging_dir)

      if raw_result and raw_result.status != common_pb.SUCCESS:
        api.python.succeeding_step(_PATCH_FIXED_BUILD_STEP_NAME, '')
        return raw_result

    # Re-apply patch so that the diff scripts can be tested via tryjobs.
    # We could build without-patch first to avoid having to apply the patch
    # twice, but it's nicer to fail fast when the patch does not compile.
    suffix = ' (with patch again)'
    with api.context(cwd=checkout_dir):
      bot_update_step = api.bot_update.ensure_checkout(suffix=suffix,
                                                       patch=True)
    api.chromium.runhooks(name='runhooks' + suffix)

    with api.context(cwd=api.path['checkout']):
      size_results_path = staging_dir.join('size_results.json')
      _CreateDiffs(api, apk_name, author, without_results_dir,
                   with_results_dir, size_results_path, staging_dir)
      expectation_success = _MaybeFailForExpectationFiles(
          api, expectations_json)
      binary_size_success = _CheckForUndocumentedIncrease(
          api, size_results_path, staging_dir, allow_regressions)
      if not expectation_success or not binary_size_success:
        raise api.step.StepFailure(
            'Failed Checks. See Failing steps for details')


def _BuildAndMeasure(api, with_patch, compile_targets, apk_name, staging_dir):
  suffix = ' (with patch)' if with_patch else ' (without patch)'
  results_basename = 'with_patch' if with_patch else 'without_patch'

  raw_result = api.chromium_tests.run_mb_and_compile(
      compile_targets, None, suffix)

  if raw_result.status != common_pb.SUCCESS:
    return None, raw_result

  results_dir = staging_dir.join(results_basename)
  api.file.ensure_directory('mkdir ' + results_basename, results_dir)

  apk_path = api.chromium_android.apk_path(apk_name)
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

  size_path = results_dir.join(apk_name + '.size')
  api.chromium_android.supersize_archive(
      apk_path, size_path, step_suffix=suffix)
  return results_dir, None


def _CheckForUndocumentedIncrease(api, results_path, staging_dir,
                                  allow_regressions):
  step_result = api.json.read(
      _RESULT_JSON_STEP_NAME, results_path,
      step_test_data=lambda: api.json.test_api.output({
        'status_code': 0,
        'summary': '\n!summary!',
        'archive_filenames': [ 'result.ndjson', 'result.txt' ],
        'links': [
            {
                'name': 'Resource Sizes Diff (high-level metrics)',
                'lines': ['!resource_sizes!'],
            }, {
                'name': 'SuperSize Text Diff',
                'lines': [u'!supersize text with \u0394!'],
            }, {
                'name': 'Dex Method Diff',
                'lines': ['!dex_methods!'],
            }, {
                'name': 'Supersize HTML Diff',
                'url': 'https://foo.com/{{result.ndjson}}',
            },
        ],
        'gerrit_plugin_details': {
          'listings': [
              {
                  'name': 'Normalised APK size',
                  'delta': '500 bytes',
                  'allowed': True,
              },
          ],
          'extras': [
              {
                  'text': 'Supersize HTML Diff',
                  'url': 'https://foo.com/{{result.ndjson}}',
              },
              {
                  'text': 'SuperSize Text Diff',
                  'url': '{{result.txt}}',
              },
          ],
        }
    }))
  result_json = step_result.json.output
  # Upload files (.ndjson) to storage bucket.
  filename_map = {}
  for filename in result_json['archive_filenames']:
    filename_map[filename] = _ArchiveArtifact(api, staging_dir, filename)

  step_result = api.python.succeeding_step(
      _RESULTS_STEP_NAME, result_json['summary'])
  for link in result_json['links']:
    if 'lines' in link:
      step_result.presentation.logs[link['name']] = link['lines']
    else:
      url = _LinkifyFilenames(link['url'], filename_map)
      step_result.presentation.links[link['name']] = url

  gerrit_plugin_details = result_json.get('gerrit_plugin_details')
  if gerrit_plugin_details:
    for extra in gerrit_plugin_details['extras']:
      if 'url' in extra:
        url = extra['url']
        url = _LinkifyFilenames(url, filename_map)
        extra['url'] = url
    step_result.presentation.properties[
        _PLUGIN_OUTPUT_PROPERTY_NAME] = gerrit_plugin_details


  if not allow_regressions and result_json['status_code'] != 0:
    step_result.presentation.status = api.step.FAILURE
    return False
  return True


def _LinkifyFilenames(url, filename_map):
  for filename, archived_url in filename_map.iteritems():
    url = url.replace('{{' + filename + '}}', archived_url)
  return url


def _CreateDiffs(api, apk_name, author, before_dir, after_dir, results_path,
                 staging_dir):
  checker_script = api.path['checkout'].join(
      'tools', 'binary_size', 'trybot_commit_size_checker.py')

  api.python('Generate diffs', checker_script, [
      '--author',
      author,
      '--apk-name',
      apk_name,
      '--before-dir',
      before_dir,
      '--after-dir',
      after_dir,
      '--results-path',
      results_path,
      '--staging-dir',
      staging_dir,
  ])


def _ArchiveArtifact(api, staging_dir, filename):
  today = api.time.utcnow().date()
  gs_dest = '{}/{}/{}/{}'.format(api.buildbucket.builder_name,
                                 today.strftime('%Y/%m/%d'),
                                 api.buildbucket.build.number, filename)
  api.gsutil.upload(
      source=staging_dir.join(filename),
      bucket=_NDJSON_GS_BUCKET,
      dest=gs_dest,
      name='archive ' + filename,
      unauthenticated_url=True)
  return _ARCHIVED_URL_PREFIX + gs_dest


def _CheckForFailedExpectationFiles(api, results_path):
  checker_script = api.resource('trybot_failed_expectations_checker.py')
  build_vars_path = api.chromium.output_dir.join(_BUILD_VARS_PATH)

  step_result = api.python('Run Expectations Script', checker_script, [
      '--check-expectations',
      '--results-path',
      api.json.output(),
      '--build-vars-path',
      build_vars_path,
  ])
  return step_result.json.output


def _MaybeFailForExpectationFiles(api, expectations_json):
  with api.step.nest(_EXPECTATIONS_STEP_NAME) as presentation:
    if not expectations_json['success']:
      presentation.status = api.step.FAILURE
      presentation.logs['failed expectations'] = '\n'.join(
          expectations_json['failed_messages'])
      return False
    return True


def _ClearFailedExpectationFiles(api):
  checker_script = api.resource('trybot_failed_expectations_checker.py')
  build_vars_path = api.chromium.output_dir.join(_BUILD_VARS_PATH)

  api.python('Clear Expectation Files', checker_script, [
      '--clear-expectations',
      '--build-vars-path',
      build_vars_path,
  ])


def GenTests(api):
  def props(name, commit_message='message', size_footer=False, **kwargs):
    kwargs.setdefault('path_config', 'kitchen')
    kwargs['revision'] = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    revision_info = {
        '_number': 1,
        'commit': {
            'author': {
                'email': 'foo@bar.com',
            },
            'message': commit_message,
        }
    }
    footer_json = {}
    if size_footer:
      footer_json['Binary-Size'] = ['Totally worth it.']
    return api.test(
        name,
        api.properties.tryserver(
            build_config='Release',
            mastername='tryserver.chromium.android',
            buildername=_TEST_BUILDER,
            buildnumber=_TEST_BUILDNUMBER,
            patch_set=1,
            **kwargs),
        api.platform('linux', 64),
        api.override_step_data(
            'gerrit changes',
            api.json.output([{
                'revisions': {
                    kwargs['revision']: revision_info
                }
            }])),
        api.override_step_data('parse description',
                               api.json.output(footer_json)),
        api.time.seed(_TEST_TIME),
    )

  def override_analyze(no_changes=False):
    """Overrides analyze step data so that targets get compiled."""
    return api.override_step_data(
        'analyze',
        api.json.output({
            'status': 'Found dependency',
            'compile_targets': _DEFAULT_ANALYZE_TARGETS,
            'test_targets': [] if no_changes else _DEFAULT_COMPILE_TARGETS}))

  def override_expectation():
    return api.step_data(
        'Run Expectations Script',
         api.json.output({'success': True, 'failed_messages':[]}))

  yield (
      props('noop_because_of_analyze') +
      api.post_check(
          lambda check, steps:
          check(steps['analyze']
                .output_properties['binary_size_plugin'] is not None)) +
      api.post_process(post_process.MustRun, 'analyze') +
      api.post_process(post_process.DoesNotRunRE, r'.*build') +
      api.post_process(post_process.DropExpectation)
  )
  yield (
      props('compile_failure') +
      override_analyze() +
      api.override_step_data('compile (with patch)', retcode=1) +
      api.post_process(post_process.StatusFailure) +
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
      override_expectation() +
      api.post_check(
          lambda check, steps:
          check(steps[_RESULTS_STEP_NAME].links['Supersize HTML Diff'] ==
                'https://foo.com/{}{}/{}/{}/result.ndjson'.format(
                    _ARCHIVED_URL_PREFIX, _TEST_BUILDER, _TEST_TIME_FMT,
                    _TEST_BUILDNUMBER))) +
      api.post_check(
          lambda check, steps:
          check(steps[_RESULTS_STEP_NAME]
                .output_properties['binary_size_plugin']['extras'][-1]['url']
                == '{}{}/{}/{}/result.txt'.format(
                  _ARCHIVED_URL_PREFIX, _TEST_BUILDER, _TEST_TIME_FMT,
                  _TEST_BUILDNUMBER))) +
      api.post_process(post_process.StepSuccess, _RESULTS_STEP_NAME)+
      api.post_process(post_process.StatusSuccess)
  )
  yield (
      props('unexpected_increase') +
      override_analyze() +
      override_expectation() +
      api.override_step_data(
         _RESULT_JSON_STEP_NAME,
         api.json.output({
             'status_code': 1,
             'summary': '\n!summary!',
             'archive_filenames': [],
             'links': [],
         })) +
      api.post_process(post_process.StepFailure, _RESULTS_STEP_NAME) +
      api.post_process(post_process.StatusFailure)
  )
  yield (
      props('expectations_file_failure') +
      override_analyze() +
      api.override_step_data(
        'Run Expectations Script',
        api.json.output({
            'success': False,
            'failed_messages': [
                'ProGuard flag expectations file needs updating. For details '
                'see:\nhttps://chromium.googlesource.com/chromium/src/+/HEAD/'
                'chrome/android/java/README.md\n',
            ]})) +
      api.post_process(post_process.StepFailure,
                       _EXPECTATIONS_STEP_NAME) +
      api.post_check(
          lambda check, steps:
          check(steps[_EXPECTATIONS_STEP_NAME].logs['failed expectations']
                is not None)) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )
  yield (
      props('pass_because_of_size_footer', size_footer=True) +
      override_analyze() +
      override_expectation() +
      api.override_step_data(
         _RESULT_JSON_STEP_NAME,
         api.json.output({
             'status_code': 1,
             'summary': '\n!summary!',
             'archive_filenames': [],
             'links': [],
         })) +
      api.post_process(post_process.StepSuccess, _RESULTS_STEP_NAME) +
      api.post_process(post_process.DropExpectation)
  )
  yield (
      props('pass_because_of_revert', commit_message='Revert some change') +
      override_analyze() +
      override_expectation() +
      api.override_step_data(
         _RESULT_JSON_STEP_NAME,
         api.json.output({
             'status_code': 1,
             'summary': '\n!summary!',
             'archive_filenames': [],
             'links': [],
         })) +
      api.post_process(post_process.StepSuccess, _RESULTS_STEP_NAME) +
      api.post_process(post_process.DropExpectation)
  )
