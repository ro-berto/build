# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from recipe_engine.engine_types import freeze

from RECIPE_MODULES.build import chromium

DEPS = [
    'chromium',
    'chromium_checkout',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/step'
]

BUILDERS = freeze({
    'chromium.clang': {
        'builders': {
            'ToTMacCoverage':
                chromium.BuilderSpec.create(
                    chromium_config='clang_tot_mac',
                    chromium_apply_config=[],
                    gclient_apply_config=['clang_tot'],
                    chromium_config_kwargs={
                        'BUILD_CONFIG': 'Release',
                        'TARGET_PLATFORM': 'mac',
                        'TARGET_BITS': 64,
                    },
                ),
            'ToTLinuxCoverage':
                chromium.BuilderSpec.create(
                    chromium_config='clang_tot_linux',
                    chromium_apply_config=[],
                    gclient_apply_config=['clang_tot'],
                    chromium_config_kwargs={
                        'BUILD_CONFIG': 'Release',
                        'TARGET_PLATFORM': 'linux',
                        'TARGET_BITS': 64,
                    },
                ),
            'ToTWindowsCoverage':
                chromium.BuilderSpec.create(
                    chromium_config='chromium_win_clang_tot',
                    chromium_apply_config=[],
                    gclient_apply_config=['clang_tot'],
                    chromium_config_kwargs={
                        'BUILD_CONFIG': 'Release',
                        'TARGET_PLATFORM': 'win',
                        'TARGET_BITS': 64,
                    },
                ),
        },
    },
})

# Sample targets that are used to test the coverage script against clang tot
# coverage tools.
SAMPLE_TARGETS = [
    'base_unittests', 'boringssl_crypto_tests', 'boringssl_ssl_tests'
]

def RunSteps(api):
  builder_id, bot_config = api.m.chromium.configure_bot(BUILDERS, ['mb'])
  with api.m.context(cwd=api.m.chromium_checkout.checkout_dir):
    _RunStepsInBuilderCacheDir(api, builder_id, bot_config)


def _RunStepsInBuilderCacheDir(api, builder_id, bot_config):
  api.bot_update.ensure_checkout()

  api.chromium.ensure_toolchains()
  api.chromium.ensure_goma()

  api.chromium.runhooks()
  clang_revision_file = api.path['checkout'].join(
      'third_party', 'llvm-build', 'Release+Asserts', 'cr_build_revision')
  revision = api.file.read_text(
      'Read clang revision', clang_revision_file, test_data='332838-1')
  api.step.active_result.presentation.step_text = revision

  api.chromium.mb_gen(builder_id, use_goma=True)

  coverage_script = 'coverage.py'
  coverage_script_path = api.path['checkout'].join('tools', 'code_coverage',
                                                   coverage_script)
  output_dir_name = 'clang_tot_coverage_report'
  output_dir_path = api.path['checkout'].join('out', output_dir_name)
  build_dir = api.chromium.output_dir

  cmd = ['python3', coverage_script_path]
  cmd.extend(SAMPLE_TARGETS)

  for target in SAMPLE_TARGETS:
    cmd.extend(['-c', build_dir.join(target)])

  cmd.extend(['-b', build_dir])
  cmd.extend(['-o', output_dir_path])

  coverage_tools_dir_path = api.path['checkout'].join(
      'third_party', 'llvm-build', 'Release+Asserts', 'bin')
  cmd.extend(['--coverage-tools-dir', coverage_tools_dir_path])

  cmd.extend(['-v'])
  with api.depot_tools.on_path():
    api.step('run coverage script', cmd)

  # Following steps are added for debugging purpose.
  for target in SAMPLE_TARGETS:
    log_file_name = '%s_output.log' % target
    log_file_path = output_dir_path.join(api.platform.name, 'logs',
                                         log_file_name)

    log_content = api.file.read_text(
        'read log output of %s' % target, log_file_path, test_data='aaa\nbbb')
    log_content_lines = log_content.splitlines()
    api.step.active_result.presentation.logs[log_file_name] = log_content_lines

  summary_file_name = 'summary.json'
  summary_file_path = output_dir_path.join(api.platform.name, summary_file_name)
  api.json.read('read %s' % summary_file_name, summary_file_path)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test
