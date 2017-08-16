# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building and running tests for WebRTC stand-alone.

DEPS = [
  'archive',
  'depot_tools/bot_update',
  'chromium',
  'chromium_android',
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
  'swarming',
  'test_utils',
  'webrtc',
]


def RunSteps(api):
  webrtc = api.webrtc
  webrtc.apply_bot_config(webrtc.BUILDERS, webrtc.RECIPE_CONFIGS)

  # TODO(kjellander): Remove when https://bugs.webrtc.org/7413 is fixed.
  if api.properties['buildername'] in ('Linux32 Debug', 'Linux32 Release'):
    step_result = api.step('Disabled: see https://bugs.webrtc.org/7413',
                           cmd=None)
    step_result.presentation.status = api.step.WARNING
    return

  webrtc.configure_swarming()

  webrtc.checkout()
  webrtc.cleanup()
  if webrtc.should_build:
    api.chromium.ensure_goma()
  api.chromium.runhooks()
  webrtc.check_swarming_version()

  if webrtc.should_build:
    webrtc.compile()

  if webrtc.should_upload_build:
    webrtc.package_build()
  if webrtc.should_upload_apprtcmobile:
    webrtc.package_apprtcmobile()
  if webrtc.should_download_build:
    webrtc.extract_build()

  if webrtc.should_test:
    webrtc.runtests()

  webrtc.maybe_trigger()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  builders = api.webrtc.BUILDERS

  def generate_builder(mastername, buildername, revision,
                       parent_got_revision=None, failing_test=None,
                       suffix=None, gerrit=False, test_output=None):
    suffix = suffix or ''
    bot_config = builders[mastername]['builders'][buildername]
    bot_type = bot_config.get('bot_type', 'builder_tester')

    if bot_type in ('builder', 'builder_tester'):
      assert bot_config.get('parent_buildername') is None, (
          'Unexpected parent_buildername for builder %r on master %r.' %
              (buildername, mastername))

    chromium_kwargs = bot_config.get('chromium_config_kwargs', {})
    test = (
      api.test('%s_%s%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername), suffix)) +
      api.properties(mastername=mastername,
                     buildername=buildername,
                     bot_id='bot_id',
                     path_config='kitchen',
                     BUILD_CONFIG=chromium_kwargs['BUILD_CONFIG']) +
      api.platform(bot_config['testing']['platform'],
                   chromium_kwargs.get('TARGET_BITS', 64))
    )

    if bot_config.get('parent_buildername'):
      test += api.properties(
          parent_buildername=bot_config['parent_buildername'])

    if revision:
      test += api.properties(revision=revision)
    if bot_type == 'tester':
      parent_rev = parent_got_revision or revision
      test += api.properties(parent_got_revision=parent_rev)

    if test_output:
      test += api.step_data('listdir webrtc_perf_tests_test_output',
                            api.file.listdir(test_output))

    if failing_test:
      test += api.step_data(failing_test, retcode=1)

    if mastername.startswith('tryserver'):
      if gerrit:
        test += api.properties.tryserver(
            mastername=mastername,
            buildername=buildername,
            gerrit_project='external/webrtc',
        )
      else:
        test += api.properties(issue=666666, patchset=1,
                               rietveld='https://fake.rietveld.url')
    test += api.properties(buildnumber=1337)

    return test

  for mastername in builders.keys():
    master_config = builders[mastername]
    for buildername in master_config['builders'].keys():
      yield generate_builder(mastername, buildername, revision='12345')

  # Test gerrit.
  mastername = 'tryserver.webrtc'
  buildername = 'linux_dbg'
  yield generate_builder(mastername, buildername, revision='12345', gerrit=True,
                         suffix='_gerrit')

  # Forced builds (not specifying any revision) and test failures.
  mastername = 'client.webrtc'
  buildername = 'Linux64 Debug'
  yield generate_builder(mastername, buildername, revision=None,
                         suffix='_forced')
  yield generate_builder(mastername, buildername, revision='12345',
                         failing_test='rtc_unittests',
                         suffix='_failing_test')

  mastername = 'client.webrtc.perf'
  yield generate_builder(mastername, 'Linux Trusty', revision='12345',
                         suffix='_test_output', test_output=['some file'])
  yield generate_builder(mastername, 'Android32 Builder', revision=None,
                         suffix='_forced')

  buildername = 'Android32 Tests (L Nexus5)'
  yield generate_builder(mastername, buildername, revision=None,
                         parent_got_revision='12345', suffix='_forced')
  yield generate_builder(mastername, buildername, revision=None,
                         suffix='_forced_invalid')
  yield generate_builder(mastername, buildername, revision='12345',
                         failing_test='webrtc_perf_tests',
                         suffix='_failing_test')
