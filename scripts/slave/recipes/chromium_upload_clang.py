# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'chromium_checkout',
  'depot_tools/depot_tools',
  'depot_tools/gsutil',
  'depot_tools/osx_sdk',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/runtime',
  'recipe_engine/step',
]


BUILDERS = freeze({
  'tryserver.chromium.linux': {
    'builders': {
      'linux_upload_clang': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },

        # 'android' is required to build the Clang toolchain with proper
        # AddressSanitizer prebuilts for Chrome on Android.
        # 'fuchsia' is required to build the builtins.a for Fuchsia.
        'gclient_apply_config': ['android', 'fuchsia'],
      },
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
      'mac_upload_clang': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
          'TARGET_BITS': 64,
        },
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win_upload_clang': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
      },
    },
  },
})


def RunSteps(api):
  _, bot_config = api.chromium.configure_bot(BUILDERS)

  api.chromium_checkout.ensure_checkout(bot_config)

  api.python('update win toolchain',
      api.path['checkout'].join('build', 'vs_toolchain.py'), ['update'])
  api.python('update mac toolchain',
      api.path['checkout'].join('build', 'mac_toolchain.py'))
  api.python('update fuchsia sdk',
      api.path['checkout'].join('build', 'fuchsia', 'update_sdk.py'))

  if api.runtime.is_luci:
    with api.osx_sdk('mac'):
      with api.depot_tools.on_path():
        api.python('download binutils',
            api.path['checkout'].join('third_party', 'binutils', 'download.py'))
        api.python(
            'package clang',
            api.path['checkout'].join(
                'tools', 'clang', 'scripts', 'package.py'),
            args=['--upload'])
  else:
    with api.depot_tools.on_path():
      api.python('download binutils',
          api.path['checkout'].join('third_party', 'binutils', 'download.py'))
      api.python(
          'package clang',
          api.path['checkout'].join('tools', 'clang', 'scripts', 'package.py'),
          args=['--upload'])


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

  yield (
      api.test('mac-luci') +
      api.platform.name('mac') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.properties.tryserver(
          buildername='mac_upload_clang',
          mastername='tryserver.chromium.mac') +
      api.buildbucket.try_build(
          project='chromium',
          builder='mac_upload_clang',
          git_repo='https://chromium.googlesource.com/chromium/src') +
      api.post_process(post_process.MustRun, 'install xcode') +
      api.post_process(post_process.MustRun, 'select XCode') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )
