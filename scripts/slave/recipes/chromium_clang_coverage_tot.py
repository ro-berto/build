# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from recipe_engine.types import freeze

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step'
]

BUILDERS = freeze({
  'chromium.clang': {
    'builders': {
      'ToTMacCoverage': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': ['clang_tot'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
          'TARGET_BITS': 64,
        },
      },
      'ToTLinuxCoverage': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': ['clang_tot'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
      },
    },
  },
})

# Sample targets that are used to test the coverage script against clang tot
# coverage tools.
SAMPLE_TARGETS = ['base_unittests', 'boringssl_crypto_tests',
                  'boringssl_ssl_tests']
SAMPLE_FUZZER_TARGETS = ['pdfium_fuzzer', 'third_party_re2_fuzzer']


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])
  api.bot_update.ensure_checkout(patch_root=bot_config.get('root_override'))

  api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.chromium.run_mb(mastername, buildername, use_goma=True)

  coverage_script = 'coverage.py'
  coverage_script_path = api.path['checkout'].join('tools', 'code_coverage',
                                                   coverage_script)
  output_dir_name = 'clang_tot_coverage_report'
  output_dir_path = api.path['checkout'].join('out', output_dir_name)
  cmd_args = []
  cmd_args.extend(SAMPLE_TARGETS)

  # TODO(crbug.com/790747): Test fuzzer targets on Mac when the bug is fixed.
  if not api.platform.is_mac:
    cmd_args.extend(SAMPLE_FUZZER_TARGETS)

  for target in SAMPLE_TARGETS:
    cmd_args.extend(['-c', api.path['checkout'].join('out', 'Release', target)])

  # TODO(crbug.com/790747): Test fuzzer targets on Mac when the bug is fixed.
  if not api.platform.is_mac:
    for fuzzer_target in SAMPLE_FUZZER_TARGETS:
      cmd_args.extend([
          '-c',
          '%s -runs=1000' % api.path['checkout'].join('out', 'Release',
                                                      fuzzer_target)
      ])

  cmd_args.extend(['-b', api.path['checkout'].join('out', 'Release')])
  cmd_args.extend(['-o', output_dir_path])

  coverage_tools_dir_path = api.path['checkout'].join(
      'third_party', 'llvm-build', 'Release+Asserts', 'bin')
  cmd_args.extend(['--coverage-tools-dir', coverage_tools_dir_path])

  cmd_args.extend(['-v'])
  api.python('run coverage script', coverage_script_path, cmd_args)

  # TODO(crbug.com/790747): Test fuzzer targets on Mac when the bug is fixed.
  executed_targets = SAMPLE_TARGETS if api.platform.is_mac else (
      SAMPLE_TARGETS + SAMPLE_FUZZER_TARGETS)

  # Following steps are added for debugging purpose.
  for target in executed_targets:
    log_file_name = '%s_output.log' % target
    log_file_path = output_dir_path.join(api.platform.name, 'logs',
                                         log_file_name)

    log_content = api.file.read_text('read log output of %s' % target,
                                     log_file_path, test_data='aaa\nbbb')
    log_content_lines = log_content.splitlines()
    api.step.active_result.presentation.logs[log_file_name] = log_content_lines

  summary_file_name = 'summary.json'
  summary_file_path = output_dir_path.join(api.platform.name, summary_file_name)
  api.json.read('read %s' % summary_file_name, summary_file_path)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test
