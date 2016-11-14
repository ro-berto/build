# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'chromium_checkout',
  'commit_position',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/tryserver',
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
  api.webrtc.checkout()
  api.gclient.runhooks()

  build_script = api.path['checkout'].join('webrtc', 'build', 'ios',
                                           'build_ios_libs.sh')
  if not api.tryserver.is_tryserver:
    api.step('cleanup', [build_script, '-c'], cwd=api.path['checkout'])

  api.step('build', [build_script, '-r', api.webrtc.revision_number],
           cwd=api.path['checkout'])

  if not api.tryserver.is_tryserver:
    output_dir = api.path['checkout'].join('out_ios_libs')
    zip_out = api.path['slave_build'].join('webrtc_ios_api_framework.zip')
    pkg = api.zip.make_package(output_dir, zip_out)
    pkg.add_directory(output_dir.join('WebRTC.framework'))
    pkg.add_directory(output_dir.join('WebRTC.dSYM'))
    # TODO(kjellander): Readd when bugs.webrtc.org/6372 is fixed.
    #pkg.add_file(output_dir.join('LICENSE.html'))
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
