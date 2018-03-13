# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'chromium_checkout',
  'commit_position',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'goma',
  'ios',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'webrtc',
  'zip',
]


def RunSteps(api):
  api.gclient.set_config('webrtc_ios')

  api.webrtc.checkout()
  api.gclient.runhooks()

  goma_dir = api.goma.ensure_goma()
  api.goma.start()
  build_exit_status = 1

  api.ios.ensure_xcode("9C40b")

  try:
    build_script = api.path['checkout'].join('tools_webrtc', 'ios',
                                             'build_ios_libs.py')
    if not api.tryserver.is_tryserver:
      api.step('cleanup', [build_script, '-c'])

    step_result = api.python(
        'build',
        build_script,
        args=['-r', api.webrtc.revision_number,
              '--use-goma',
              '--extra-gn-args=goma_dir=\"%s\"' % goma_dir,
              '--verbose'],
    )
    build_exit_status = step_result.retcode
  except api.step.StepFailure as e:
    build_exit_status = e.retcode
    raise e
  finally:
    api.goma.stop(ninja_log_compiler='goma',
                  build_exit_status=build_exit_status)

  if not api.tryserver.is_tryserver:
    output_dir = api.path['checkout'].join('out_ios_libs')
    zip_out = api.path['start_dir'].join('webrtc_ios_api_framework.zip')
    pkg = api.zip.make_package(output_dir, zip_out)
    pkg.add_directory(output_dir.join('WebRTC.framework'))
    pkg.zip('zip archive')

    api.gsutil.upload(
        zip_out,
        'chromium-webrtc',
        ('ios_api_framework/webrtc_ios_api_framework_%s.zip' %
         api.webrtc.revision_number),
        args=['-a', 'public-read'],
        unauthenticated_url=True)


def GenTests(api):
  yield (
    api.test('build_ok') +
    api.properties.generic(mastername='client.webrtc',
                           buildername='iOS API Framework Builder',
                           path_config='kitchen')
  )

  yield (
    api.test('build_failure') +
    api.properties.generic(mastername='client.webrtc',
                           buildername='iOS API Framework Builder',
                           path_config='kitchen') +
    api.step_data('build', retcode=1)
  )

  yield (
    api.test('trybot_build') +
    api.properties.tryserver(mastername='tryserver.webrtc',
                             buildername='ios_api_framework',
                             path_config='kitchen')
  )
