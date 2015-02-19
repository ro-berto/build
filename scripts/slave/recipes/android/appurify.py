# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

DEPS = [
  'amp',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'path',
  'properties',
  'step',
]

CHROMIUM_AMP_UNITTESTS = [
  ['android_webview_unittests', None],
  ['base_unittests', ['base', 'base_unittests.isolate']],
  ['cc_unittests', None],
  ['components_unittests', ['components', 'components_unittests.isolate']],
  ['events_unittests', None],
  ['skia_unittests', None],
  ['sql_unittests', ['sql', 'sql_unittests.isolate']],
  ['ui_android_unittests', None],
  ['ui_touch_selection_unittests', None],
]

BUILDERS = {
  'Android Tests (amp)(dbg)': {
    'config': 'main_builder',
    'target': 'Debug',
    'download': {
      'bucket': 'chromium-android',
      'path': lambda api: ('android_fyi_dbg/full-build-linux_%s.zip' %
                           api.properties['revision']),
    },
    'device_name': ['Nexus 4', 'Nexus 5', 'Nexus 7', 'Nexus 9', 'Nexus 10'],
    'device_os': ['4.1.1', '4.2.1', '4.2.2', '4.3', '4.4.2', '4.4.3', '5.0'],
    'unittests': CHROMIUM_AMP_UNITTESTS,
    'instrumentation_tests': [],
  },
}

REPO_URL = 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src'

AMP_INSTANCE_ADDRESS = '172.22.21.180'
AMP_INSTANCE_PORT = '80'
AMP_INSTANCE_PROTOCOL = 'http'
AMP_RESULTS_BUCKET = 'chrome-amp-results'

def GenSteps(api):
  builder = BUILDERS[api.properties['buildername']]
  # TODO(jbudorick): Does this need to be done?
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

  api.chromium_android.download_build(builder['download']['bucket'],
                                      builder['download']['path'](api))
  extract_location = api.chromium_android.out_path.join(
                         api.chromium_android.c.BUILD_CONFIG)
  api.step('remove extract location',
           ['rm', '-rf', extract_location])
  api.step('move extracted build',
           ['mv', '-T', api.path['checkout'].join('full-build-linux'),
                        extract_location])

  with api.step.defer_results():
    for suite, isolate_file in builder.get('unittests', []):
      isolate_file_path = (
          api.path['checkout'].join(*isolate_file) if isolate_file else None)
      api.amp.trigger_test_suite(
          suite, 'gtest',
          api.amp.gtest_arguments(suite, isolate_file_path=isolate_file_path),
          api.amp.amp_arguments(api_address=AMP_INSTANCE_ADDRESS,
                                api_port=AMP_INSTANCE_PORT,
                                api_protocol=AMP_INSTANCE_PROTOCOL,
                                device_name=builder.get('device_name'),
                                device_os=builder.get('device_os')))

    for suite, isolate_file in builder.get('unittests', []):
      deferred_step_result = api.amp.collect_test_suite(
          suite, 'gtest',
          api.amp.gtest_arguments(suite),
          api.amp.amp_arguments(api_address=AMP_INSTANCE_ADDRESS,
                                api_port=AMP_INSTANCE_PORT,
                                api_protocol=AMP_INSTANCE_PROTOCOL,
                                device_name=builder.get('device_name'),
                                device_os=builder.get('device_os')))
      if not deferred_step_result.is_ok:
        api.amp.upload_logcat_to_gs(AMP_RESULTS_BUCKET, suite)


def GenTests(api):
  sanitize = lambda s: ''.join(c if c.isalnum() else '_' for c in s)

  for buildername in BUILDERS:
    yield (
        api.test('%s_basic' % sanitize(buildername)) +
        api.properties.generic(
            revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
            parent_buildername='parent_buildername',
            parent_buildnumber='1729',
            buildername=buildername,
            slavename='slavename',
            mastername='tryserver.chromium.linux',
            buildnumber='1337')
    )

    yield (
      api.test('%s_test_failure' % sanitize(buildername)) +
      api.properties.generic(
          revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
          parent_buildername='parent_buildername',
          parent_buildnumber='1729',
          buildername=buildername,
          slavename='slavename',
          mastername='tryserver.chromium.linux',
          buildnumber='1337') +
      api.step_data('[collect] android_webview_unittests', retcode=1)
    )