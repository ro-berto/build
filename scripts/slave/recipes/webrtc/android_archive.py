# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_checkout',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'goma',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'webrtc',
]


def RunSteps(api):
  api.gclient.set_config('webrtc')
  api.gclient.apply_config('android')

  api.webrtc.checkout()
  api.gclient.runhooks()

  goma_dir = api.goma.ensure_goma()
  api.goma.start()
  ninja_log_exit_status = 1
  try:
    build_script = api.path['checkout'].join('tools_webrtc', 'android',
                                             'build_aar.py')
    with api.context(cwd=api.path['checkout']):
      step_result = api.python(
          'build',
          build_script,
          args=['--use-goma',
                '--verbose',
                '--extra-gn-args', 'goma_dir=\"%s\"' % goma_dir],
      )
    ninja_log_exit_status = step_result.retcode
  except api.step.StepFailure as e:
    ninja_log_exit_status = e.retcode
    raise e
  finally:
    api.goma.stop(ninja_log_compiler='goma',
                  ninja_log_exit_status=ninja_log_exit_status)

  if not api.tryserver.is_tryserver:
    api.gsutil.upload(
        api.path['checkout'].join('libwebrtc.aar'),
        'chromium-webrtc',
        'android_archive/webrtc_android_%s.aar' % api.webrtc.revision_number,
        args=['-a', 'public-read'],
        unauthenticated_url=True)


def GenTests(api):
  yield (
    api.test('build_ok') +
    api.properties.generic(mastername='client.webrtc.fyi',
                           buildername='Android Archive',
                           path_config='kitchen')
  )

  yield (
    api.test('build_failure') +
    api.properties.generic(mastername='client.webrtc.fyi',
                           buildername='Android Archive',
                           path_config='kitchen') +
    api.step_data('build', retcode=1)
  )

  yield (
    api.test('trybot_build') +
    api.properties.tryserver(mastername='tryserver.webrtc',
                             buildername='android_archive',
                             path_config='kitchen')
  )
