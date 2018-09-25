# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'chromium_checkout',
  'chromium_tests',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gerrit',
  'depot_tools/tryserver',
  'filter',
  'gn',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

BUILDERS = freeze({
  'tryserver.chromium.linux': {
    'builders': {
      'linux-libfuzzer-asan-rel': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
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

INCLUDED_FUZZ_TARGETS = ['//testing/libfuzzer:libfuzzer_main']
EXCLUDED_FUZZ_TARGETS = ['//testing/libfuzzer:no_clusterfuzz']


def RunSteps(api):
  assert api.tryserver.is_tryserver

  with api.chromium.chromium_layout():
    mastername = api.m.properties['mastername']
    buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])

    bot_config = {}
    checkout_dir = api.chromium_checkout.get_checkout_dir(bot_config).join(
        'src')
    with api.context(cwd=checkout_dir):
      api.chromium_checkout.ensure_checkout(bot_config)
      outdir = api.chromium.output_dir

      api.chromium.runhooks()
      api.chromium.ensure_goma()
      api.chromium.mb_gen(mastername, buildername, use_goma=True)

      # Calculate the GN labels of all fuzz targets.
      all_fuzz_labels = api.gn.refs(
          outdir, INCLUDED_FUZZ_TARGETS, output_type='executable',
          step_name='calculate all_fuzzers', output_format='label')
      excluded_fuzz_labels = api.gn.refs(
          outdir, EXCLUDED_FUZZ_TARGETS, output_type='executable',
          step_name='calculate no_fuzzers', output_format='label')
      fuzz_labels = list(all_fuzz_labels - excluded_fuzz_labels)

      # Filter out all targets that the patch doesn't affect.
      affected_files = api.chromium_checkout.get_files_affected_by_patch()
      test_targets, compile_targets = api.filter.analyze(
          affected_files, None, fuzz_labels, 'trybot_analyze_config.json')
      affected_fuzz_labels = test_targets + compile_targets
      if not affected_fuzz_labels:
        return

      # Run MB one more time since filter calls above wipes out the specified
      # goma dir.
      api.chromium.mb_gen(
          mastername, buildername, use_goma=True, gn_args_location=api.gn.LOGS)

      # Convert the GN labels to ninja targets and pass them into compile.
      affected_fuzz_targets = list(api.gn.ls(
          outdir, affected_fuzz_labels, output_format='output'))
      api.chromium.compile(targets=affected_fuzz_targets, use_goma_module=True)


def GenTests(api):
  yield (
    api.test('basic_linux_tryjob') +
    api.properties.tryserver(mastername='tryserver.chromium.linux',
                             buildername='linux-libfuzzer-asan-rel') +
    api.step_data('calculate all_fuzzers',
        stdout=api.raw_io.output_text(
            '//foo/bar:target1\n//foo/bar:target2\n//foo/bar:target3')) +
    api.step_data('calculate no_fuzzers',
        stdout=api.raw_io.output_text('//foo/bar:target1'))
  )

  yield (
    api.test('basic_linux_tryjob_with_compile') +
    api.properties.tryserver(mastername='tryserver.chromium.linux',
                             buildername='linux-libfuzzer-asan-rel') +
    api.step_data('calculate all_fuzzers',
        stdout=api.raw_io.output_text(
            '\n'.join(['//foo/bar:target1', '//foo/bar:target2',
                       '//foo/bar:target3']))) +
    api.step_data('calculate no_fuzzers',
        stdout=api.raw_io.output_text('//foo/bar:target1')) +
    api.override_step_data(
        'analyze',
        api.json.output({
            'status': 'Found dependency',
            'compile_targets': ['//foo/bar:target2'],
            'test_targets': []})) +
    api.step_data('list gn targets',
        stdout=api.raw_io.output_text('target2'))
  )
