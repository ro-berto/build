# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'ios',
  'recipe_engine/buildbucket',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
]

def RunSteps(api):
  # Clang and WebKit tip-of-tree bots need to have a gclient config
  # applied. Since the build config hasn't been checked out yet, it can't be
  # specified there.
  gclient_apply_config = []
  if api.m.properties['mastername'] == 'chromium.clang':
    gclient_apply_config = ['clang_tot']
  elif api.m.buildbucket.builder_name == 'ios-webkit-tot':
    gclient_apply_config = ['ios_webkit_tot']

  api.ios.checkout(gclient_apply_config)
  api.ios.read_build_config()
  api.ios.build()
  if api.runtime.is_experimental:
    result = api.step('Skip upload', [])
    result.presentation.step_text = (
        'Running in experimental mode, skipping upload.')
  else:
    api.ios.upload()
  api.ios.test_swarming()

def GenTests(api):

  def verify_webkit_custom_vars(check, step_odict, expected):
    # Verifies that the command for the "bot_update" step either contains or
    # does not contain the strings "checkout_ios_webkit" and
    # "ios_webkit_revision". Does not verify that these custom_vars are set
    # correctly, only that the strings appear.
    step = step_odict['bot_update']
    found_checkout_ios_webkit = False
    found_ios_webkit_revision = False
    for arg in step.cmd:
      if 'checkout_ios_webkit' in arg:
        found_checkout_ios_webkit = True
      if 'ios_webkit_revision' in arg:
        found_ios_webkit_revision = True
    check(expected == found_checkout_ios_webkit)
    check(expected == found_ios_webkit_revision)

  basic_common = (
      api.platform('mac', 64) + api.properties(
          mastername='chromium.fake',
          bot_id='fake-vm',
      ) + api.buildbucket.try_build(
          project='chromium',
          builder='ios',
          build_number=1,
          revision='HEAD',
          git_repo='https://chromium.googlesource.com/chromium/src',
      ) + api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'env': {
              'fake env var 1': 'fake env value 1',
              'fake env var 2': 'fake env value 2',
          },
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'bucket':
              'fake-bucket-1',
          'tests': [
              {
                  'app': 'fake tests 1',
                  'device type': 'fake device',
                  'os': '8.0',
              },
              {
                  'app': 'fake tests 2',
                  'device type': 'fake device',
                  'os': '7.1',
              },
              {
                  'app': 'fake_eg_test_host',
                  'device type': 'fake device 3',
                  'os': '9.3',
                  'xctest': True,
              },
          ],
          'upload': [
              {
                  'artifact': 'fake tests 1.app',
                  'compress': True,
              },
              {
                  'artifact': 'fake tests 2.app',
                  'bucket': 'fake-bucket-2',
              },
          ],
      }) + api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ))

  yield api.test(
      'basic',
      basic_common,
      api.post_process(verify_webkit_custom_vars, False),
  )

  yield api.test(
      'basic_experimental',
      basic_common,
      api.runtime(is_luci=True, is_experimental=True),
  )

  yield api.test(
      'goma',
      api.platform('mac', 64),
      api.properties(
          mastername='chromium.fake',
          bot_id='fake-vm',
      ),
      api.buildbucket.try_build(
          project='chromium',
          builder='ios',
          build_number=1,
          revision='HEAD',
          git_repo='https://chromium.googlesource.com/chromium/src',
      ),
      api.ios.make_test_build_config({
          'xcode version': 'fake xcode version',
          'gn_args': [
              'is_debug=false',
              'target_cpu="arm"',
              'use_goma=true',
          ],
          'tests': [],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
  )

  yield api.test(
      'goma_canary',
      api.platform('mac', 64),
      api.properties(
          mastername='chromium.fake',
          bot_id='fake-vm',
      ),
      api.buildbucket.try_build(
          project='chromium',
          builder='ios',
          build_number=1,
          revision='HEAD',
          git_repo='https://chromium.googlesource.com/chromium/src',
      ),
      api.ios.make_test_build_config({
          'xcode version': 'fake xcode version',
          'gn_args': [
              'is_debug=false',
              'target_cpu="arm"',
              'use_goma=true',
          ],
          'goma_client_type': 'candidate',
          'tests': [],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
  )

  yield api.test(
      'goma_compilation_failure',
      api.platform('mac', 64),
      api.properties(
          mastername='chromium.fake',
          bot_id='fake-vm',
      ),
      api.buildbucket.try_build(
          project='chromium',
          builder='ios',
          build_number=1,
          revision='HEAD',
          git_repo='https://chromium.googlesource.com/chromium/src',
      ),
      api.ios.make_test_build_config({
          'xcode version':
              '6.1.1',
          'gn_args': [
              'is_debug=false',
              'target_cpu="arm"',
              'use_goma=true',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'compile',
          retcode=1,
          stdout=api.raw_io.output_text('1.2.3'),
      ),
  )

  yield api.test(
      'clang-tot',
      api.platform('mac', 64),
      api.properties(
          mastername='chromium.clang',
          bot_id='fake-vm',
      ),
      api.buildbucket.try_build(
          project='chromium',
          builder='ios',
          build_number=1,
          revision='HEAD',
          git_repo='https://chromium.googlesource.com/chromium/src',
      ),
      api.ios.make_test_build_config({
          'xcode version': 'fake xcode version',
          'gn_args': [
              'is_debug=false',
              'target_cpu="arm"',
          ],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ios-webkit-tot',
      api.platform('mac', 64),
      api.properties(
          mastername='chromium.fake',
          bot_id='fake-vm',
      ),
      api.buildbucket.try_build(
          project='chromium',
          builder='ios-webkit-tot',
          build_number=1,
          revision='HEAD',
          git_repo='https://chromium.googlesource.com/chromium/src',
      ),
      api.ios.make_test_build_config({
          'xcode version': 'fakexcodeversion-customwebkit',
          'gn_args': [
              'is_debug=false',
              'target_cpu="arm"',
          ],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      api.post_process(verify_webkit_custom_vars, True),
      api.post_process(post_process.DropExpectation),
  )
