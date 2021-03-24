# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.archive import properties
from RECIPE_MODULES.build.chromium_tests import (steps, try_spec as
                                                 try_spec_module)
from recipe_engine import post_process

DEPS = [
    'archive',
    'chromium',
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  try_spec = api.chromium_tests.trybots.get(builder_id)
  try_spec = try_spec_module.TrySpec.create(mirrors=[builder_id])
  bot_config = api.chromium_tests.create_bot_config_object(try_spec.mirrors)
  api.chromium_tests.configure_build(bot_config)
  build_dir = api.path.abspath(
      api.path.join(api.path['checkout'], 'out',
                    api.chromium.c.build_config_fs))
  api.archive.generic_archive(
      build_dir=build_dir,
      update_properties=api.properties.get('update_properties'),
      custom_vars=api.properties.get('custom_vars'))


def GenTests(api):
  input_properties = properties.InputProperties()
  cipd_archive_data = properties.CIPDArchiveData()
  cipd_archive_data.yaml_files.extend(['foo'])
  cipd_archive_data.tags['version'] = '{%chrome_version%}'
  cipd_archive_data.pkg_vars['targetarch'] = '{%arch%}'
  cipd_archive_data.compression.compression_level = 8
  input_properties.cipd_archive_datas.extend([cipd_archive_data])

  yield api.test(
      'fuchsia_cipd_archive_arm64',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='fuchsia-fyi-arm64-size'),
      api.properties(
          cipd_archive=True,
          update_properties={},
          custom_vars={
              'chrome_version': '1.2.3.4',
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.StepCommandContains,
                       "Generic Archiving Steps.create foo", [
                           'cipd', 'create', '-pkg-def', 'None/out/Release/foo',
                           '-hash-algo', 'sha256', '-tag', 'version:1.2.3.4',
                           '-pkg-var', 'targetarch:arm64', '-compression-level',
                           '8', '-json-output', '/path/to/tmp/json'
                       ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'fuchsia_cipd_archive_x64',
      api.chromium.generic_build(
          builder_group='chromium.fyi', builder='fuchsia-fyi-x64-rel'),
      api.properties(
          cipd_archive=True,
          update_properties={},
          custom_vars={
              'chrome_version': '1.2.3.4',
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.StepCommandContains,
                       "Generic Archiving Steps.create foo", [
                           'cipd', 'create', '-pkg-def', 'None/out/Release/foo',
                           '-hash-algo', 'sha256', '-tag', 'version:1.2.3.4',
                           '-pkg-var', 'targetarch:amd64', '-compression-level',
                           '8', '-json-output', '/path/to/tmp/json'
                       ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'android_cipd_archive_arm32',
      api.chromium.generic_build(
          builder_group='chromium.clang', builder='ToTAndroidASan'),
      api.properties(
          cipd_archive=True,
          update_properties={},
          custom_vars={
              'chrome_version': '1.2.3.4',
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.StepCommandContains,
                       "Generic Archiving Steps.create foo", [
                           'cipd', 'create', '-pkg-def', 'None/out/Release/foo',
                           '-hash-algo', 'sha256', '-tag', 'version:1.2.3.4',
                           '-pkg-var', 'targetarch:arm32', '-compression-level',
                           '8', '-json-output', '/path/to/tmp/json'
                       ]),
      api.post_process(post_process.DropExpectation),
  )
