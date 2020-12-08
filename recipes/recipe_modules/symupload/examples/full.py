# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from PB.recipe_modules.build.symupload import properties
from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import (steps, try_spec as
                                                 try_spec_module)

DEPS = [
    'chromium',
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

  api_key_path = None
  kms_crypto_key = None
  if api.properties.get('run_api_key'):
    api_key_path = api.path['cleanup'].join('api_key')
    api.path.mock_add_paths(api_key_path)
    kms_crypto_key = 'projects/cryptoKeys/symupload-api-key'

  api.symupload(
      api.path['tmp_base'],
      kms_crypto_key=kms_crypto_key,
      api_key_path=api_key_path,
      experimental=api.properties.get('experimental'))


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
      'win_symupload_v2',
      api.properties(
          target_platform='win', host_platform='win', run_api_key=True),
      api.path.exists(api.path['tmp_base'].join('symupload.exe')),
      api.symupload(input_properties),
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
      api.properties(
          target_platform='linux', host_platform='linux', run_api_key=True),
      api.path.exists(api.path['tmp_base'].join('symupload')),
      api.symupload(input_properties),
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
