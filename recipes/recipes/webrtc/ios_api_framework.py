# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'archive',
    'builder_group',
    'chromium',
    'chromium_checkout',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/gsutil',
    'depot_tools/tryserver',
    'infra/zip',
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

  api.webrtc.ensure_xcode("12d4e")

  build_script = api.path['checkout'].join('tools_webrtc', 'ios',
                                           'build_ios_libs.py')
  if api.tryserver.is_tryserver:
    build_revision_number_args = []
  else:
    api.step('cleanup', [build_script, '-c'])
    build_revision_number_args = ['-r', api.webrtc.revision_number]

  api.python(
      'build',
      build_script,
      # TODO(https://bugs.webrtc.org/11349): re-enable Goma once we figure out
      # why it's failing to find clang-1100.0.33.16 in the Goma backend.
      args=['--verbose'] + build_revision_number_args,
  )

  output_dir = api.path['checkout'].join('out_ios_libs')

  api.webrtc.get_binary_sizes(
      files=['WebRTC.xcframework/ios-arm64/WebRTC.framework/WebRTC'],
      base_dir=output_dir)

  if not api.tryserver.is_tryserver:
    zip_out = api.path['start_dir'].join('webrtc_ios_api_framework.zip')
    pkg = api.zip.make_package(output_dir, zip_out)
    pkg.add_directory(output_dir.join('WebRTC.framework'))
    pkg.zip('zip archive')

    if not api.runtime.is_experimental:
      api.gsutil.upload(
          zip_out,
          'chromium-webrtc',
          ('ios_api_framework/webrtc_ios_api_framework_%s.zip' %
           api.webrtc.revision_number),
          args=['-a', 'public-read'],
          unauthenticated_url=True)


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
