# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'archive',
    'builder_group',
    'chromium',
    'chromium_checkout',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'goma',
    'ios',
    'recipe_engine/commit_position',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'webrtc',
]


def RunSteps(api):
  api.gclient.set_config('webrtc_ios')

  api.webrtc.checkout()
  api.gclient.runhooks()

  goma_dir = api.goma.ensure_goma()
  api.goma.start()
  build_exit_status = 1

  api.webrtc.ensure_xcode("13a233")

  try:
    build_script = api.path['checkout'].join('tools_webrtc', 'ios',
                                             'build_ios_libs.py')
    if api.tryserver.is_tryserver:
      build_revision_number_args = []
    else:
      api.step('cleanup', [build_script, '-c'])
      build_revision_number_args = ['-r', api.webrtc.revision_number]

    step_result = api.python(
        'build',
        build_script,
        args=[
            '--use-goma',
            '--extra-gn-args=goma_dir=\"%s\"' % goma_dir, '--verbose'
        ] + build_revision_number_args,
    )
    build_exit_status = step_result.retcode
  except api.step.StepFailure as e:
    build_exit_status = e.retcode
    raise e
  finally:
    api.goma.stop(
        ninja_log_compiler='goma', build_exit_status=build_exit_status)

  output_dir = api.path['checkout'].join('out_ios_libs')

  api.webrtc.get_binary_sizes(
      files=['WebRTC.xcframework/ios-arm64/WebRTC.framework/WebRTC'],
      base_dir=output_dir)


def GenTests(api):
  yield api.test(
      'build_ok',
      api.builder_group.for_current('client.webrtc'),
      api.properties.generic(buildername='iOS API Framework Builder'),
  )

  yield api.test(
      'build_failure',
      api.builder_group.for_current('client.webrtc'),
      api.properties.generic(buildername='iOS API Framework Builder'),
      api.step_data('build', retcode=1),
  )

  yield api.test(
      'trybot_build',
      api.builder_group.for_current('tryserver.webrtc'),
      api.properties.tryserver(
          buildername='ios_api_framework',
          gerrit_url='https://webrtc-review.googlesource.com',
          gerrit_project='src'),
  )
