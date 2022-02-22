# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import attr
import functools

from recipe_engine import post_process
from recipe_engine.engine_types import freeze
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'depot_tools/bot_update',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'ios',
    'recipe_engine/resultdb',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'webrtc',
]

PUBLIC_TEST_SERVICE_ACCOUNT = (
    'chromium-tester@chops-service-accounts.iam.gserviceaccount.com')
INTERNAL_TEST_SERVICE_ACCOUNT = (
    'chrome-tester@chops-service-accounts.iam.gserviceaccount.com')

RECIPE_CONFIGS = freeze({
  'webrtc_ios': {
    'chromium_config': 'webrtc_default',
    'gclient_config': 'webrtc_ios',
    'test_suite': 'ios',
  },
  'webrtc_ios_device': {
    'chromium_config': 'webrtc_default',
    'gclient_config': 'webrtc_ios',
    'test_suite': 'ios_device',
  },
  'webrtc_ios_perf': {
    'chromium_config': 'webrtc_default',
    'gclient_config': 'webrtc_ios',
    'test_suite': 'ios_perf',
  },
})

BUILDERS = freeze({
    'luci.webrtc.try': {
        'settings': {
            'builder_group': 'tryserver.webrtc',
        },
        'builders': {
            'ios_compile_arm64_dbg': {
                'recipe_config': 'webrtc_ios',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
                'ensure_sdk': 'ios',
                'ios_config': {
                    'sdk': 'iphoneos10.3',
                },
            },
            'ios_compile_arm64_rel': {
                'recipe_config': 'webrtc_ios',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
                'ensure_sdk': 'ios',
                'ios_config': {
                    'sdk': 'iphoneos10.3',
                },
            },
            'ios_sim_x64_dbg_ios14': {
                'recipe_config': 'webrtc_ios',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'ensure_sdk': 'ios',
                'ios_testing': {
                    'device type': 'iPhone X',
                    'os': '14.0',
                    'host os': 'Mac-11',
                },
            },
            'ios_sim_x64_dbg_ios13': {
                'recipe_config': 'webrtc_ios',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'ensure_sdk': 'ios',
                'ios_testing': {
                    'device type': 'iPhone X',
                    'os': '13.6',
                    'host os': 'Mac-11',
                },
            },
            'ios_sim_x64_dbg_ios12': {
                'recipe_config': 'webrtc_ios',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'ensure_sdk': 'ios',
                'ios_testing': {
                    'device type': 'iPhone X',
                    'os': '12.4',
                    'host os': 'Mac-11',
                },
            },
        },
    },
})


def RunSteps(api):
  webrtc = api.webrtc
  webrtc.apply_bot_config(BUILDERS, RECIPE_CONFIGS)

  webrtc.checkout()

  webrtc.configure_swarming()

  api.chromium.ensure_goma()
  api.chromium.runhooks()

  with api.step.nest('apply build config'):
    webrtc.apply_ios_config()

  with webrtc.ensure_sdk():
    if not webrtc.is_compile_needed(is_ios=True):
      step_result = api.step('No further steps are necessary.', cmd=None)
      step_result.presentation.status = api.step.SUCCESS
      return
    webrtc.configure_isolate()
    webrtc.run_mb_ios()
    raw_result = webrtc.compile()
    if raw_result.status != common_pb.SUCCESS:
      return raw_result

  if webrtc.bot.should_test:
    swarming_service_account = webrtc.bot.config.get(
        'swarming_service_account', PUBLIC_TEST_SERVICE_ACCOUNT)
    if swarming_service_account:
      api.ios.swarming_service_account = swarming_service_account
    with api.step.nest('isolate'):
      tasks = api.ios.isolate()
    triggered_tests = []
    with api.step.nest('trigger'):
      result_callback = result_callback = lambda **kw: True
      resultdb = attr.evolve(
          ResultDB.create(),
          result_format='json',
          result_file='${ISOLATED_OUTDIR}/output.json',
      )
      for task in tasks:
        test = api.ios.generate_test_from_task(
            task,
            result_callback=result_callback,
            use_rdb=True,
            resultdb=resultdb)
        if test:
          test.pre_run(suffix='')
          api.resultdb.include_invocations([
              i[len('invocations/'):]
              for i in test.get_task('').get_invocation_names()
          ])
          triggered_tests.append(test)
    api.ios.collect(triggered_tests)


def GenTests(api):
  builders = BUILDERS
  generate_builder = functools.partial(api.webrtc.generate_builder, builders)

  for bucketname in builders.keys():
    group_config = builders[bucketname]
    for buildername in group_config['builders'].keys():
      yield (
          generate_builder(bucketname, buildername, revision='a' * 40) +
          # The version is just a placeholder, don't bother updating it:
          api.properties(**{'$depot_tools/osx_sdk': {'sdk_version': '10l232m'}})
      )

  yield (generate_builder(
      'luci.webrtc.try',
      'ios_compile_arm64_dbg',
      revision='b' * 40,
      suffix='_fail_compile',
      fail_compile=True) +
         api.properties(**{'$depot_tools/osx_sdk': {
             'sdk_version': '10l232m'
         }}) + api.post_process(post_process.StatusFailure) +
         api.post_process(post_process.DropExpectation))

  gn_analyze_no_deps_output = {'status': ['No dependency']}
  yield (generate_builder(
      'luci.webrtc.try',
      'ios_sim_x64_dbg_ios14',
      revision='a' * 40,
      suffix='_gn_analyze_no_dependency',
      gn_analyze_output=gn_analyze_no_deps_output) +
         api.properties(**{'$depot_tools/osx_sdk': {
             'sdk_version': '12a7209'
         }}))
  gn_analyze_no_deps_output = {'status': ['No dependency']}
  yield (generate_builder(
      'luci.webrtc.try',
      'ios_compile_arm64_dbg',
      revision='a' * 40,
      suffix='_gn_analyze_no_dependency',
      gn_analyze_output=gn_analyze_no_deps_output) +
         api.properties(**{'$depot_tools/osx_sdk': {
             'sdk_version': '10l232m'
         }}))
