# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze
from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

DEPS = [
  'archive',
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
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
      'Afl Upload Linux ASan': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clobber' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'upload_bucket': 'chromium-browser-afl',
        'upload_directory': 'asan',
      },
    },
  },
})


def gn_refs(api, step_name, args):
  """Runs gn refs with given additional arguments.
  Returns: the list of matched targets.
  """
  step_result = api.python(step_name,
          api.depot_tools.gn_py_path,
          ['--root=%s' % str(api.path['checkout']),
           'refs',
           str(api.chromium.output_dir),
          ] + args,
          stdout=api.raw_io.output_text())
  return step_result.stdout.split()


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])

  checkout_results = api.bot_update.ensure_checkout(
      patch_root=bot_config.get('root_override'))

  api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.chromium.mb_gen(mastername, buildername)

  all_fuzzers = gn_refs(
          api,
          'calculate all_fuzzers',
          ['--all',
           '--type=executable',
           '--as=output',
           '//testing/libfuzzer:libfuzzer_main'])
  no_clusterfuzz = gn_refs(
          api,
          'calculate no_clusterfuzz',
          ['--all',
           '--type=executable',
           '--as=output',
           '//testing/libfuzzer:no_clusterfuzz'])
  targets = list(set(all_fuzzers).difference(set(no_clusterfuzz)))
  api.step.active_result.presentation.logs['all_fuzzers'] = all_fuzzers
  api.step.active_result.presentation.logs['no_clusterfuzz'] = no_clusterfuzz
  api.step.active_result.presentation.logs['targets'] = targets
  raw_result = api.chromium.compile(targets=targets, use_goma_module=True)
  if raw_result.status != common_pb.SUCCESS:
    return raw_result

  api.archive.clusterfuzz_archive(
          build_dir=api.chromium.output_dir,
          update_properties=checkout_results.json.output['properties'],
          gs_bucket=bot_config['upload_bucket'],
          archive_prefix='afl',
          archive_subdir_suffix=bot_config['upload_directory'],
          gs_acl='public-read')


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield (test +
           api.step_data('calculate all_fuzzers',
               stdout=api.raw_io.output_text('target1 target2 target3')) +
           api.step_data('calculate no_clusterfuzz',
               stdout=api.raw_io.output_text('target1'))
           )

  yield (
      api.test('compile_failure') +
      api.properties.generic(
          mastername='chromium.fuzz',
          buildername='Afl Upload Linux ASan'
      ) +
      api.step_data('compile', retcode=1) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )
