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
  'gsutil',
  'path',
  'properties',
  'python',
  'step',
]

CHROMIUM_AMP_UNITTESTS = [
  ['base_unittests', ['base', 'base_unittests.isolate']],
  ['cc_unittests', None],
  ['events_unittests', None],
]

BUILDERS = {
  'amp-tests': {
    'config': 'main_builder',
    'target': 'Debug',
    'download': {
      'bucket': 'chromium-android',
      'path': lambda api: ('android_fyi_dbg/full-build-linux_%s.zip' %
                           api.properties['revision']),
    },
    'unittests': CHROMIUM_AMP_UNITTESTS,
    'instrumentation_tests': [],
  },
}

REPO_URL = 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src'

AMP_INSTANCE_ADDRESS = '172.22.21.180'
AMP_INSTANCE_PORT = '80'
AMP_INSTANCE_PROTOCOL = 'http'


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
    trigger_dir = api.path.mkdtemp('amp_trigger')
    def trigger_file(suite):
      return trigger_dir.join('%s.pickle' % suite)
    for suite, isolate_file in builder.get('unittests', []):
      isolate_file_path = (
          api.path['checkout'].join(*isolate_file) if isolate_file else None)
      api.amp.run_android_test_suite(
          '%s (trigger)' % suite,
          'gtest',
          api.amp.gtest_arguments(suite, isolate_file_path=isolate_file_path),
          api.amp.amp_arguments(api_address=AMP_INSTANCE_ADDRESS,
                                api_port=AMP_INSTANCE_PORT,
                                api_protocol=AMP_INSTANCE_PROTOCOL,
                                trigger=trigger_file(suite)))
    api.amp.run_android_test_suite(
        'uirobot (trigger)', 'uirobot',
        api.amp.uirobot_arguments(minutes=5),
        api.amp.amp_arguments(api_address=AMP_INSTANCE_ADDRESS,
                              api_port=AMP_INSTANCE_PORT,
                              api_protocol=AMP_INSTANCE_PROTOCOL,
                              trigger=trigger_file('uirobot')))

    for suite, isolate_file in builder.get('unittests', []):
      api.amp.run_android_test_suite(
          '%s (collect)' % suite,
          'gtest',
          api.amp.gtest_arguments(suite),
          api.amp.amp_arguments(api_address=AMP_INSTANCE_ADDRESS,
                                api_port=AMP_INSTANCE_PORT,
                                api_protocol=AMP_INSTANCE_PROTOCOL,
                                collect=trigger_file(suite)))

    api.amp.run_android_test_suite(
      'uirobot (collect)', 'uirobot',
      api.amp.uirobot_arguments(),
      api.amp.amp_arguments(api_address=AMP_INSTANCE_ADDRESS,
                            api_port=AMP_INSTANCE_PORT,
                            api_protocol=AMP_INSTANCE_PROTOCOL,
                            collect=trigger_file('uirobot')))

def GenTests(api):
  for buildername in BUILDERS:
    yield (
        api.test('%s_basic' % buildername) +
        api.properties.generic(
            revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
            parent_buildername='parent_buildername',
            parent_buildnumber='1729',
            buildername=buildername,
            slavename='slavename',
            mastername='tryserver.chromium.linux',
            buildnumber='1337')
    )

