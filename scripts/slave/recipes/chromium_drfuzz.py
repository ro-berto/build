# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze


DEPS = [
  'archive',
  'bot_update',
  'chromium',
  'file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]


BUILDERS = freeze({
  'chromium.fyi': {
    'builders': {
      'Win LKGR (DrM)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'upload_bucket': 'chromium-browser-drfuzz',
        'upload_directory': 'chromium_win32',
        'bot_type': 'builder',
      },
      'Win LKGR (DrM 64)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'upload_bucket': 'chromium-browser-drfuzz',
        'upload_directory': 'chromium_win64',
        'bot_type': 'builder',
      },
    },
  },
})


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])

  checkout_results = api.bot_update.ensure_checkout(
      force=True, patch_root=bot_config.get('root_override'))

  api.chromium.runhooks()

  api.chromium.run_mb(mastername, buildername, use_goma=False)

  step_result = api.python('calculate targets',
          api.path['depot_tools'].join('gn.py'),
          ['--root=%s' % str(api.path['checkout']),
           'refs',
           str(api.chromium.output_dir),
           '--all',
           '--type=executable',
           '--as=output',
           '//testing/libfuzzer:libfuzzer_main',
          ],
          stdout=api.raw_io.output())

  targets = step_result.stdout.split()
  api.step.active_result.presentation.logs['targets'] = targets
  api.chromium.compile(targets=targets)

  api.archive.clusterfuzz_archive(
          build_dir=api.path['slave_build'].join('src', 'out', 'Release'),
          update_properties=checkout_results.json.output['properties'],
          gs_bucket=bot_config['upload_bucket'],
          archive_prefix='drfuzz',
          archive_subdir_suffix=bot_config['upload_directory'],
          gs_acl='public-read')

def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield (test +
           api.step_data('calculate targets',
               stdout=api.raw_io.output('target1 target2 target3'))
           )

