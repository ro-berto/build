# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'adb',
    'bot_update',
    'chromium_android',
    'gclient',
    'json',
    'step',
    'path',
    'properties',
    'python',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

BUILDERS = {
  'android_nexus5-oilpan-perf': {},
}

def GenSteps(api):
  # TODO(zty): implement this recipe
  #buildername = api.properties['buildername']
  #builder = BUILDERS[buildername]
  api.chromium_android.configure_from_properties('base_config',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')

  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.gclient.apply_config('chrome_internal')
  yield api.bot_update.ensure_checkout()
  yield api.chromium_android.cleanup_build()

def GenTests(api):
  for buildername in BUILDERS:
    yield (
        api.test('test_%s' % buildername) +
        api.properties.generic(
            repo_name='src',
            repo_url=REPO_URL,
            buildername=buildername,
            parent_buildername='parent_buildername',
            parent_buildnumber='1729',
            revision='deadbeef',
            slavename='slavename',
            target='Release')
    )
