# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import functools

from recipe_engine import post_process
from recipe_engine.engine_types import freeze


PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
  'archive',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'chromium',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'webrtc',
]


BUILDERS = freeze({
    'luci.webrtc.ci': {
        'settings': {
            'builder_group': 'client.webrtc',
        },
        'builders': {
            'Linux64 Release (Libfuzzer)': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
        },
    },
    'luci.webrtc.try': {
        'settings': {
            'builder_group': 'tryserver.webrtc',
        },
        'builders': {
            'linux_libfuzzer_rel': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
        },
    },
})


def RunSteps(api):
  webrtc = api.webrtc
  webrtc.apply_bot_config(BUILDERS, webrtc.RECIPE_CONFIGS)

  webrtc.checkout()
  api.chromium.ensure_goma()
  api.chromium.runhooks()
  webrtc.run_mb()

  with api.context(cwd=api.path['checkout']):
    args = [
        '--root=%s' % str(api.path['checkout']),
        'refs',
        str(api.chromium.output_dir),
        '--all',
        '--type=executable',
        '--as=output',
        '//test/fuzzers:webrtc_fuzzer_main',
    ]
    script = str(api.depot_tools.gn_py_path)
    cmd = ['vpython3', '-u', script] + args
    step_result = api.step(
        'calculate targets', cmd, stdout=api.raw_io.output_text())

  targets = step_result.stdout.split()
  api.step.active_result.presentation.logs['targets'] = targets
  return api.chromium.compile(targets=targets, use_goma_module=True)


def GenTests(api):
  builders = BUILDERS
  generate_builder = functools.partial(api.webrtc.generate_builder, builders)

  for bucketname in builders.keys():
    group_config = builders[bucketname]
    for buildername in group_config['builders'].keys():
      yield (generate_builder(bucketname, buildername, revision='a' * 40) +
             api.step_data('calculate targets',
                 stdout=api.raw_io.output_text('target1 target2 target3')))
  yield (generate_builder(
      'luci.webrtc.ci',
      'Linux64 Release (Libfuzzer)',
      revision='a' * 40,
      suffix='_compile_failure',
      fail_compile=True) + api.post_process(post_process.StatusFailure) +
         api.post_process(post_process.DropExpectation))
