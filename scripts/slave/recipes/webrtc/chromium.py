# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building Chromium and running WebRTC-specific tests with special
# requirements that doesn't allow them to run in the main Chromium waterfalls.
# Also provide a set of FYI bots that builds Chromium with WebRTC ToT to provide
# pre-roll test results.

DEPS = [
  'archive',
  'bot_update',
  'chromium',
  'chromium_android',
  'chromium_tests',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step',
  'test_utils',
  'webrtc',
]


def RunSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  webrtc = api.webrtc

  if api.platform.is_win:
    api.chromium.taskkill()

  # TODO(kjellander): Continue refactoring so we can use the generic chromium
  # recipe instead, if possible.
  api.chromium_tests.configure_build(mastername, buildername)

  if mastername == 'chromium.webrtc.fyi':
    # Sync HEAD revisions for Chromium, WebRTC and Libjingle.
    # This is used for some bots to provide data about which revisions are green
    # to roll into Chromium.
    p = api.properties
    revs = {
      'src': p.get('parent_got_revision', 'HEAD'),
      'src/third_party/webrtc': p.get('parent_got_webrtc_revision', 'HEAD'),
      'src/third_party/libjingle/source/talk': p.get(
          'parent_got_libjingle_revision', 'HEAD'),
    }
    for path, revision in revs.iteritems():
      api.gclient.c.revisions[path] = revision

  update_step, master_dict, test_spec = \
      api.chromium_tests.prepare_checkout(mastername, buildername)

  api.chromium_tests.compile(mastername, buildername, update_step, master_dict,
                             test_spec)

  # TODO(kjellander): Figure out a cleaner way to handle the sizes step;
  # possibly build it into chromium_tests.prepare_checkout or the test spec.
  bot_config = master_dict.get('builders', {}).get(buildername)
  if (bot_config['bot_type'] in ('builder', 'builder_tester') and
      mastername == 'chromium.webrtc.fyi' and
      api.chromium.c.TARGET_PLATFORM != 'android'):
    api.chromium.sizes(results_url=webrtc.DASHBOARD_UPLOAD_URL,
                       perf_id=bot_config.get('perf-id'),
                       perf_config=webrtc.WEBRTC_REVISION_PERF_CONFIG)

  tests = api.chromium_tests.tests_for_builder(
      mastername, buildername, update_step, master_dict)

  if not tests:
    return
  test_runner = api.chromium_tests.create_test_runner(api, tests)
  with api.chromium_tests.wrap_chromium_tests(mastername, tests):
    test_runner()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  builders = api.chromium_tests.builders
  CR_REV = 'c321321'
  LIBJINGLE_REV = '1161aa63'
  WEBRTC_REV = 'deadbeef'

  def generate_builder(mastername, buildername, revision=None,
                       failing_test=None, suffix=None):
    suffix = suffix or ''
    bot_config = builders[mastername]['builders'][buildername]
    bot_type = bot_config.get('bot_type', 'builder_tester')

    if bot_type in ('builder', 'builder_tester'):
      assert bot_config.get('parent_buildername') is None, (
          'Unexpected parent_buildername for builder %r on master %r.' %
              (buildername, mastername))
    test = (
      api.test('%s_%s%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername), suffix)) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             revision=revision,
                             parent_buildername=bot_config.get(
                                 'parent_buildername')) +
      api.platform(bot_config['testing']['platform'],
                   bot_config.get(
                       'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
    )
    if bot_config.get('parent_buildername'):
      test += api.properties(parent_got_revision=CR_REV)

      if mastername.endswith('.fyi'):
        test += api.properties(parent_got_libjingle_revision=LIBJINGLE_REV,
                               parent_got_webrtc_revision=WEBRTC_REV)

    if mastername.endswith('.fyi'):
      test += api.properties(got_revision=CR_REV,
                             got_libjingle_revision=LIBJINGLE_REV,
                             got_webrtc_revision=WEBRTC_REV)
    if bot_type in ('builder_tester', 'tester'):
      # TODO(kjellander): Reduce this JSON for better readability. It's kept
      # like this to make the initial review easier.
      if (bot_config['chromium_config_kwargs'].get('TARGET_PLATFORM')
          != 'android'):
        test += api.override_step_data('read test spec', api.json.output({
          buildername: {
            'gtest_tests': [
              {
                'swarming': {
                  'can_use_on_swarming_builders': False
                },
                'test': 'content_unittests'
              }
            ],
            'scripts': [
              {
                'args': [
                  'browser_tests',
                  '--gtest_filter=WebRtc*:Webrtc*:TabCapture*:*MediaStream*',
                  '--run-manual',
                  '--ui-test-action-max-timeout=350000',
                  '--test-launcher-jobs=1',
                  '--test-launcher-bot-mode',
                  '--test-launcher-print-test-stdio=always'
                ],
                'name': 'browser_tests',
                'script': 'gtest_perf_test.py'
              },
              {
                'args': [
                  'content_browsertests',
                  '--gtest_filter=WebRtc*',
                  '--run-manual',
                  '--test-launcher-print-test-stdio=always',
                  '--test-launcher-bot-mode'
                ],
                'name': 'content_browsertests',
                'script': 'gtest_perf_test.py'
              }
            ]
          }
        }))
    if failing_test:
      test += api.step_data(failing_test, retcode=1)

    return test

  for mastername in ('chromium.webrtc', 'chromium.webrtc.fyi'):
    master_config = builders[mastername]
    for buildername in master_config['builders'].keys():
      # chromium.webrtc.fyi builders are triggered on WebRTC revisions and it's
      # passed as a build property to the builder. However it's ignored since
      # these builders only build 'HEAD' for Chromium, WebRTC and libjingle.
      # That means got_revision and parent_got_revision will still be a Chromium
      # Git hash for these builders.
      revision = WEBRTC_REV if mastername == 'chromium.webrtc.fyi' else CR_REV
      yield generate_builder(mastername, buildername, revision)

  # Forced build (not specifying any revision) and failing tests.
  mastername = 'chromium.webrtc'
  yield generate_builder(mastername, 'Linux Builder', suffix='_forced')

  buildername = 'Linux Tester'
  yield generate_builder(mastername, buildername, suffix='_forced_invalid')
  yield generate_builder(mastername, buildername,
                         failing_test='content_browsertests',
                         suffix='_failing_test')

  # Periodic scheduler triggered builds also don't contain revision.
  mastername = 'chromium.webrtc.fyi'
  yield generate_builder(mastername, 'Win Builder',
                         suffix='_periodic_triggered')

  # Testers gets got_revision value from builder passed as parent_got_revision.
  yield generate_builder(mastername, 'Win7 Tester',
                         suffix='_periodic_triggered')
  yield generate_builder(mastername, 'Android Tests (dbg) (L Nexus9)',
                         failing_test='content_browsertests',
                         suffix='_failing_test')
