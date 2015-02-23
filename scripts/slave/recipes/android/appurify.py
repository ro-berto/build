# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze
from slave import recipe_api

DEPS = [
  'amp',
  'bot_update',
  'chromium',
  'chromium_android',
  'filter',
  'gclient',
  'itertools',
  'json',
  'path',
  'properties',
  'step',
  'tryserver',
]

CHROMIUM_AMP_UNITTESTS = freeze([
  ['android_webview_unittests', None],
  ['base_unittests', ['base', 'base_unittests.isolate']],
  ['cc_unittests', None],
  ['components_unittests', ['components', 'components_unittests.isolate']],
  ['events_unittests', None],
  ['skia_unittests', None],
  ['sql_unittests', ['sql', 'sql_unittests.isolate']],
  ['ui_android_unittests', None],
  ['ui_touch_selection_unittests', None],
])

JAVA_UNIT_TESTS = freeze([
  'junit_unit_tests',
])

PYTHON_UNIT_TESTS = freeze([
  'gyp_py_unittests',
  'pylib_py_unittests',
])

BUILDERS = freeze({
  'tryserver.chromium.linux': {
    'android_amp_rel_tests_recipe': {
      'config': 'main_builder',
      'target': 'Release',
      'build': True,
      'try': True,
      'device_name': ['Nexus 5'],
      'device_os': ['4.4.2', '4.4.3'],
      'unittests': CHROMIUM_AMP_UNITTESTS,
      'instrumentation_tests': [],
      'java_unittests': JAVA_UNIT_TESTS,
      'python_unittests': PYTHON_UNIT_TESTS,
    },
  },
  'chromium.fyi': {
    'Android Tests (amp)(dbg)': {
      'config': 'main_builder',
      'target': 'Debug',
      'build': False,
      'download': {
        'bucket': 'chromium-android',
        'path': lambda api: ('android_fyi_dbg/full-build-linux_%s.zip' %
                             api.properties['revision']),
      },
      'device_name': ['Nexus 4', 'Nexus 5', 'Nexus 6', 'Nexus 7', 'Nexus 10'],
      'device_os': ['4.1.1', '4.2.1', '4.2.2', '4.3', '4.4.2', '4.4.3', '5.0'],
      'device_timeout': 60,
      'unittests': CHROMIUM_AMP_UNITTESTS,
      'instrumentation_tests': [],
    },
  },
  'chromium.linux': {
    'EXAMPLE_android_amp_builder_tester': {
      'config': 'main_builder',
      'target': 'Release',
      'build': True,
      'device_name': ['Nexus 5'],
      'device_os': ['4.4.2', '4.4.3'],
      'unittests': CHROMIUM_AMP_UNITTESTS,
      'instrumentation_tests': [],
      'java_unittests': JAVA_UNIT_TESTS,
      'python_unittests': PYTHON_UNIT_TESTS,
    }
  }
})

REPO_URL = 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src'

AMP_INSTANCE_ADDRESS = '172.22.21.180'
AMP_INSTANCE_PORT = '80'
AMP_INSTANCE_PROTOCOL = 'http'
AMP_RESULTS_BUCKET = 'chrome-amp-results'

def GenSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  builder = BUILDERS[mastername][buildername]
  api.chromium_android.configure_from_properties(
      builder['config'],
      REPO_NAME='src',
      REPO_URL=REPO_URL,
      INTERNAL=False,
      BUILD_CONFIG=builder['target'])

  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.gclient.apply_config('chrome_internal')

  api.bot_update.ensure_checkout()
  api.chromium_android.clean_local_files()
  api.chromium.runhooks()

  api.chromium_android.run_tree_truth()

  native_unittests = builder.get('unittests', [])
  instrumentation_tests = [
      api.chromium_android.get_instrumentation_suite(s)
      for s in builder.get('instrumentation_tests', [])]
  java_unittests = builder.get('java_unittests', [])
  python_unittests = builder.get('python_unittests', [])

  if builder.get('build', False):
    test_names = []
    test_names.extend(suite for suite, _ in native_unittests)
    test_names.extend(suite['gyp_target'] for suite in instrumentation_tests)
    test_names.extend(java_unittests)

    compile_targets = api.chromium.c.compile_py.default_targets

    if builder.get('try', False):
      api.tryserver.maybe_apply_issue()

      api.filter.does_patch_require_compile(
          exes=test_names,
          compile_targets=compile_targets,
          additional_name='chromium',
          config_file_name='trybot_analyze_config.json')
      if not api.filter.result:
        return
      compile_targets = (
          list(set(compile_targets) & set(api.filter.compile_targets))
          if compile_targets
          else api.filter.compile_targets)
      native_unittests = [
          i for i in native_unittests
          if i[0] in api.filter.matching_exes]
      instrumentation_tests = [
          i for i in instrumentation_tests
          if i['gyp_target'] in api.filter.matching_exes]
      java_unittests = [
          i for i in java_unittests
          if i in api.filter.matching_exes]

    api.chromium_android.run_tree_truth()
    api.chromium.compile(targets=compile_targets)

  if not instrumentation_tests and not native_unittests and not java_unittests:
    return

  download_config = builder.get('download')
  if download_config:
    api.chromium_android.download_build(download_config['bucket'],
                                        download_config['path'](api))
    extract_location = api.chromium_android.out_path.join(
                           api.chromium_android.c.BUILD_CONFIG)
    api.step('remove extract location',
             ['rm', '-rf', extract_location])
    api.step('move extracted build',
             ['mv', '-T', api.path['checkout'].join('full-build-linux'),
                          extract_location])

  with api.step.defer_results():
    for suite, isolate_file in native_unittests:
      isolate_file_path = (
          api.path['checkout'].join(*isolate_file) if isolate_file else None)
      api.amp.trigger_test_suite(
          suite, 'gtest',
          api.amp.gtest_arguments(suite, isolate_file_path=isolate_file_path),
          api.amp.amp_arguments(api_address=AMP_INSTANCE_ADDRESS,
                                api_port=AMP_INSTANCE_PORT,
                                api_protocol=AMP_INSTANCE_PROTOCOL,
                                device_name=builder.get('device_name'),
                                device_os=builder.get('device_os'),
                                device_timeout=builder.get('device_timeout')))

    # TODO(jbudorick): Add support for instrumentation tests.

    for suite in java_unittests:
      api.chromium_android.run_java_unit_test_suite(suite)

    for suite in python_unittests:
      api.chromium_android.run_python_unit_test_suite(suite)

    for suite, isolate_file in native_unittests:
      deferred_step_result = api.amp.collect_test_suite(
          suite, 'gtest',
          api.amp.gtest_arguments(suite),
          api.amp.amp_arguments(api_address=AMP_INSTANCE_ADDRESS,
                                api_port=AMP_INSTANCE_PORT,
                                api_protocol=AMP_INSTANCE_PROTOCOL,
                                device_name=builder.get('device_name'),
                                device_os=builder.get('device_os'),
                                device_timeout=builder.get('device_timeout')))
      if not deferred_step_result.is_ok:
        api.amp.upload_logcat_to_gs(AMP_RESULTS_BUCKET, suite)


def GenTests(api):
  sanitize = lambda s: ''.join(c if c.isalnum() else '_' for c in s)

  for mastername in BUILDERS:
    master = BUILDERS[mastername]
    for buildername in master:
      builder = master[buildername]

      test_props = (
          api.test('%s_basic' % sanitize(buildername)) +
          api.properties.generic(
              revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
              buildername=buildername,
              slavename='slavename',
              mastername=mastername))
      if builder.get('try'):
        test_props += api.override_step_data(
            'analyze',
            api.json.output({
                'status': 'Found dependency',
                'targets': ['base_unittests', 'junit_unit_tests'],
                'build_targets': ['base_unittests_apk', 'junit_unit_tests']}))
      yield test_props

      yield (
        api.test('%s_test_failure' % sanitize(buildername)) +
        api.properties.generic(
            revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
            buildername=buildername,
            slavename='slavename',
            mastername=mastername) +
        api.override_step_data(
            'analyze',
            api.json.output({
                'status': 'Found dependency',
                'targets': ['android_webview_unittests'],
                'build_targets': ['android_webview_unittests_apk']})) +
        api.step_data('[collect] android_webview_unittests', retcode=1)
      )

  yield (
      api.test('analyze_no_compilation') +
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='android_amp_rel_tests_recipe',
          slavename='slavename') +
      api.override_step_data(
          'analyze', api.json.output({'status': 'No compile necessary'})))

  yield (
      api.test('analyze_no_tests') +
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='android_amp_rel_tests_recipe',
          slavename='slavename') +
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'targets': [],
              'build_targets': ['base_unittests']})))
