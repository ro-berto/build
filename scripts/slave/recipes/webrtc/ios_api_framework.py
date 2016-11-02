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

  checkout_kwargs = {}
  checkout_dir = api.chromium_checkout.get_checkout_dir({})
  if checkout_dir:
    checkout_kwargs['cwd'] = checkout_dir
  update_step = api.bot_update.ensure_checkout(**checkout_kwargs)

  # TODO(ehmaldonado): Remove when the iOS API framework script is ported over
  # to GN. See bugs.webrtc.org/6372
  if api.properties['buildername'] == 'iOS API Framework Builder':
    step_result = api.step('Disabled until the iOS API framework script is '
                           'ported over to GN. See bugs.webrtc.org/6372',
                           cmd=None)
    step_result.presentation.status = api.step.WARNING
    return

  revs = update_step.presentation.properties
  commit_pos = api.commit_position.parse_revision(revs['got_revision_cp'])
  api.gclient.runhooks()

  build_script = api.path['checkout'].join('webrtc', 'build', 'ios',
                                           'build_ios_libs.sh')
  if not api.tryserver.is_tryserver:
    api.step('cleanup', [build_script, '-c'], cwd=api.path['checkout'])

  api.step('build', [build_script, '-r', commit_pos], cwd=api.path['checkout'])

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
        'ios_api_framework/webrtc_ios_api_framework_%d.zip' % commit_pos,
        args=['-a', 'public-read'],
        unauthenticated_url=True)


def GenTests(api):
  # TODO(ehmaldonado): Rename to 'iOS API Framework Builder' when the iOS API
  # framework script is ported over to GN. See bugs.webrtc.org/6372
  yield (
    api.test('build_ok') +
    api.properties.generic(mastername='client.webrtc',
                           buildername='iOS API Framework',
                           path_config='kitchen')
  )

  # TODO(ehmaldonado): Remove when the iOS API framework script is ported over
  # to GN. See bugs.webrtc.org/6372
  yield (
    api.test('build_disabled') +
    api.properties.generic(mastername='client.webrtc',
                           buildername='iOS API Framework Builder',
                           path_config='kitchen')
  )

  # TODO(ehmaldonado): Rename to 'iOS API Framework Builder' when the iOS API
  # framework script is ported over to GN. See bugs.webrtc.org/6372
  yield (
    api.test('build_failure') +
    api.properties.generic(mastername='client.webrtc',
                           buildername='iOS API Framework',
                           path_config='kitchen') +
    api.step_data('build', retcode=1)
  )

  yield (
    api.test('trybot_build') +
    api.properties.tryserver(mastername='tryserver.webrtc',
                             buildername='ios_api_framework',
                             path_config='kitchen')
  )
