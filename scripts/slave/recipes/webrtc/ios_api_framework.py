# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'commit_position',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'file',
  'gsutil',
  'ios',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'webrtc',
  'zip',
]


def RunSteps(api):
  api.gclient.set_config('webrtc_ios')

  api.ios.host_info()
  update_step = api.bot_update.ensure_checkout()
  revs = update_step.presentation.properties
  commit_pos = api.commit_position.parse_revision(revs['got_revision_cp'])
  api.gclient.runhooks()

  build_script = api.path['checkout'].join('webrtc', 'build', 'ios',
                                           'build_ios_framework.sh')
  api.step('cleanup', [build_script, '-c'], cwd=api.path['checkout'])

  api.step('build', [build_script, '-r', commit_pos], cwd=api.path['checkout'])

  output_dir = api.path['checkout'].join('out_ios_libs')
  zip_out = api.path['slave_build'].join('webrtc_ios_api_framework.zip')
  pkg = api.zip.make_package(output_dir, zip_out)
  pkg.add_directory(output_dir.join('WebRTC.framework'))
  pkg.add_directory(output_dir.join('WebRTC.framework.dSYM'))
  pkg.zip('zip archive')

  api.gsutil.upload(
      zip_out,
      'chromium-webrtc',
      'ios_api_framework/webrtc_ios_api_framework_%d.zip' % commit_pos,
      args=['-a', 'public-read'],
      unauthenticated_url=True)


def GenTests(api):
  yield (
    api.test('build_ok') +
    api.properties.generic(mastername='client.webrtc.fyi',
                           buildername='iOS API Framework Builder')
  )

  yield (
    api.test('build_failure') +
    api.properties.generic(mastername='client.webrtc.fyi',
                           buildername='iOS API Framework Builder') +
    api.step_data('build', retcode=1)
  )
