# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
from recipe_engine.types import freeze

DEPS = [
  'archive',
  'chromium',
  'chromium_checkout',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'gn',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]


BUILDERS = freeze({
  'chromium.fuzz': {
    'builders': {
      'Libfuzzer Upload Chrome OS ASan': {
        'archive_prefix': 'libfuzzer-chromeos',
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'chromeos',
          'TARGET_BITS': 64,
        },
        'gclient_apply_config': ['chromeos'],
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'chromeos-asan',
      },
      'Libfuzzer Upload Linux32 ASan': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 32,
        },
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'asan',
      },
      'Libfuzzer Upload Linux32 ASan Debug': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 32,
        },
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'asan',
      },
      'Libfuzzer Upload Linux ASan': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'asan',
      },
      'Libfuzzer Upload Linux ASan Debug': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'asan',
      },
      'Libfuzzer Upload Linux MSan': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': ['clobber', 'msan' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'msan',
      },
      'Libfuzzer Upload Linux UBSan': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'ubsan',
      },
      'Libfuzzer Upload Mac ASan': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
          'TARGET_BITS': 64,
        },
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'asan',
      },
      'Libfuzzer Upload Windows ASan': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 64,
        },
        'upload_bucket': 'chromium-browser-libfuzzer',
        'upload_directory': 'asan',
      },
    },
  },
})


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])

  checkout_results = api.chromium_checkout.ensure_checkout(bot_config)

  api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.chromium.mb_gen(mastername, buildername, use_goma=True)

  with api.context(cwd=api.path['checkout'], env=api.chromium.get_env()):
    all_fuzzers = api.gn.refs(
        api.chromium.output_dir,
        ['//testing/libfuzzer:libfuzzer_main'],
        output_type='executable',
        output_format='output',
        step_name='calculate all_fuzzers')
    no_clusterfuzz = api.gn.refs(
        api.chromium.output_dir,
        ['//testing/libfuzzer:no_clusterfuzz'],
        output_type='executable',
        output_format='output',
        step_name='calculate no_clusterfuzz')
  targets = list(all_fuzzers - no_clusterfuzz)
  api.step.active_result.presentation.logs['all_fuzzers'] = all_fuzzers
  api.step.active_result.presentation.logs['no_clusterfuzz'] = no_clusterfuzz
  api.step.active_result.presentation.logs['targets'] = targets
  api.chromium.compile(targets=targets, use_goma_module=True)

  # Make sure 32 bit archives are distinguished from 64 bit ones.
  kwargs = {}
  if api.chromium.c.TARGET_BITS == 32:
    kwargs['use_legacy'] = False
    kwargs['bitness'] = 32

  api.archive.clusterfuzz_archive(
      build_dir=api.chromium.output_dir,
      update_properties=checkout_results.json.output['properties'],
      gs_bucket=bot_config['upload_bucket'],
      archive_prefix=bot_config.get('archive_prefix', 'libfuzzer'),
      archive_subdir_suffix=bot_config['upload_directory'],
      gs_acl='public-read',
      **kwargs)

def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield (test +
           api.step_data('calculate all_fuzzers',
               stdout=api.raw_io.output_text('target1\ntarget2\ntarget3')) +
           api.step_data('calculate no_clusterfuzz',
               stdout=api.raw_io.output_text('target1'))
           )

  yield (
      api.test('kitchen_paths') +
      api.platform.name('mac') +
      api.properties.generic(
          mastername='chromium.fuzz',
          buildername='Libfuzzer Upload Mac ASan',
          path_config='kitchen'))
