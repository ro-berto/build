# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'bot_update',
  'chromium',
  'file',
  'raw_io',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


BUILDERS = freeze({
  'chromium.fyi': {
    'builders': {
      'Libfuzzer Upload Linux': {
        'chromium_apply_config': [ 'proprietary_codecs' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
      },
    },
  },
})


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])

  api.bot_update.ensure_checkout(
      force=True, patch_root=bot_config.get('root_override'))

  api.chromium.runhooks()

  # checkout llvm
  api.step('checkout llvm',
           [api.path.sep.join(['tools', 'clang', 'scripts', 'update.sh']),
            '--force-local-build',
            '--without-android'],
           cwd=api.path['checkout'],
           env={'LLVM_FORCE_HEAD_REVISION': 'YES'})

  api.chromium.run_mb(mastername, buildername, use_goma=False)

  step_result = api.python('calculate targets',
          api.path['depot_tools'].join('gn.py'),
          ['--root=%s' % str(api.path['checkout']),
           'refs',
           str(api.chromium.output_dir),
           '--type=executable',
           '--as=output',
           '//testing/libfuzzer:libfuzzer_main',
          ],
          stdout=api.raw_io.output())

  targets = step_result.stdout.split()
  api.step.active_result.presentation.logs['targets'] = targets
  api.chromium.compile(targets=targets)

def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield (test +
           api.step_data("calculate targets",
               stdout=api.raw_io.output("target1 target2 target3"))
           )

