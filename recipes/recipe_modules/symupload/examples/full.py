# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
from recipe_engine import post_process

from PB.recipe_modules.build.symupload import properties

DEPS = [
    'chromium',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'symupload',
]


def RunSteps(api):
  api.chromium.set_config(
      'chromium', **{
          'TARGET_PLATFORM': api.properties.get('target_platform'),
          'HOST_PLATFORM': api.properties.get('host_platform')
      })

  api.symupload(
      api.path['tmp_base'], experimental=api.properties.get('experimental'))


def GenTests(api):
  input_properties = properties.InputProperties()
  symupload_data = input_properties.symupload_datas.add()

  symupload_data.artifact = 'some_artifact.txt'
  symupload_data.url = 'https://some.url.com'
  symupload_data.file_globs.append('glob*.txt')

  yield api.test(
      'basic_win',
      api.properties(target_platform='win', host_platform='win'),
      api.path.exists(api.path['tmp_base'].join('symupload.exe')),
      api.symupload(input_properties),
      api.post_process(post_process.StatusSuccess),
  )

  yield api.test(
      'basic_win_override_win_toolchain_json',
      api.properties(target_platform='win', host_platform='win'),
      api.override_step_data(
          'symupload.find_win_toolchain',
          api.file.read_json({
              'path':
                  'C:\\src\\chromium\\src\\win_toolchain\\20d5f2553f',
              'runtime_dirs': [
                  'C:\\src\\chromium\\src\\win_toolchain\\20d5f2553f\\sys64',
                  'C:\\src\\chromium\\src\\win_toolchain\\20d5f2553f\\sys32',
              ],
          })),
      api.path.exists(api.path['tmp_base'].join('symupload.exe')),
      api.symupload(input_properties),
      api.post_process(post_process.StatusSuccess),
  )

  yield api.test(
      'basic_linux/mac',
      api.properties(target_platform='mac', host_platform='mac'),
      api.path.exists(api.path['tmp_base'].join('symupload')),
      api.symupload(input_properties),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no symupload binary',
      api.properties(target_platform='win', host_platform='win'),
      api.symupload(input_properties),
      api.post_process(post_process.StepFailure, 'symupload'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no action',
      api.properties(target_platform='mac', host_platform='mac'),
      api.symupload(properties.InputProperties()),
      api.post_process(post_process.DoesNotRun, 'symupload'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'experimental',
      api.properties(
          target_platform='linux', host_platform='linux', experimental=True),
      api.path.exists(api.path['tmp_base'].join('symupload')),
      api.symupload(input_properties),
      api.post_process(post_process.DoesNotRun, 'symupload.symupload'),
      api.post_process(post_process.DoesNotRun, 'symupload.symupload_v2'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  encoded_api_key = base64.b64encode('encrypted_api_key')

  input_properties_v2 = properties.InputProperties()
  symupload_data = input_properties_v2.symupload_datas.add()
  symupload_data.artifacts.append('some_artifact.txt')
  symupload_data.url = 'https://some.url.com'
  symupload_data.file_globs.append('glob*.txt')
  symupload_data.base64_api_key = encoded_api_key
  symupload_data.kms_key_path = "some/path"

  yield api.test(
      'win_symupload_v2',
      api.properties(target_platform='win', host_platform='win'),
      api.path.exists(api.path['tmp_base'].join('symupload.exe')),
      api.symupload(input_properties_v2),
      api.post_process(post_process.MustRun, 'symupload.symupload_v2'),
      api.post_process(post_process.StepCommandContains,
                       'symupload.symupload_v2', [
                           '--api-key-file',
                           '[CLEANUP]/symupload-api-key.txt',
                       ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'linux/mac_symupload_v2',
      api.properties(target_platform='linux', host_platform='linux'),
      api.path.exists(api.path['tmp_base'].join('symupload')),
      api.symupload(input_properties_v2),
      api.post_process(post_process.MustRun, 'symupload.symupload_v2'),
      api.post_process(post_process.StepCommandContains,
                       'symupload.symupload_v2', [
                           '--api-key-file',
                           '[CLEANUP]/symupload-api-key.txt',
                       ]),
      api.post_process(post_process.StatusSuccess),
  )

  symupload_data.artifact_type = "dsym"
  yield api.test(
      'mac_symupload_v2',
      api.properties(target_platform='mac', host_platform='mac'),
      api.path.exists(api.path['tmp_base'].join('symupload')),
      api.symupload(input_properties_v2),
      api.post_process(post_process.MustRun, 'symupload.symupload_v2'),
      api.post_process(post_process.StepCommandContains,
                       'symupload.symupload_v2', [
                           '--artifact_type',
                           'dsym',
                       ]),
      api.post_process(post_process.StatusSuccess),
  )

  input_properties_v2 = properties.InputProperties()
  symupload_data = input_properties_v2.symupload_datas.add()
  symupload_data.artifacts.append('some_artifact.txt')
  symupload_data.url = 'https://some.url.com'
  symupload_data.file_globs.append('glob*.txt')
  symupload_data.base64_api_key = encoded_api_key

  yield api.test(
      'linux/mac_symupload_v2_missing_kms_key',
      api.properties(target_platform='linux', host_platform='linux'),
      api.path.exists(api.path['tmp_base'].join('symupload')),
      api.symupload(input_properties_v2),
      api.post_process(post_process.StepFailure, 'symupload'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
