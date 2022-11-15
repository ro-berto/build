# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import textwrap

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

from PB.recipe_modules.build.chromium_tests_builder_config_migration import (
    properties as properties_pb)

DEPS = [
    'chromium_tests_builder_config',
    'chromium_tests_builder_config_migration',
    'recipe_engine/properties',
]

PROPERTIES = properties_pb.InputProperties


def RunSteps(api, properties):
  ctbc_api = api.chromium_tests_builder_config
  return api.chromium_tests_builder_config_migration(properties,
                                                     ctbc_api.builder_db,
                                                     ctbc_api.try_db)


def GenTests(api):
  expected_snippets = textwrap.dedent("""\
      bar-group:bar-builder
          builder_spec = builder_config.builder_spec(
              gclient_config = builder_config.gclient_config(
                  config = "chromium",
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium",
              ),
          ),

      bar-group:bar-tester
          builder_spec = builder_config.builder_spec(
              execution_mode = builder_config.execution_mode.TEST,
              gclient_config = builder_config.gclient_config(
                  config = "chromium",
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium",
              ),
          ),

      foo-group:foo-builder
          builder_spec = builder_config.builder_spec(
              gclient_config = builder_config.gclient_config(
                  config = "gclient-config1",
                  apply_configs = [
                      "gclient-config2",
                      "gclient-config3",
                  ],
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium-config1",
                  apply_configs = [
                      "chromium-config2",
                      "chromium-config3",
                  ],
                  build_config = builder_config.build_config.RELEASE,
                  target_arch = builder_config.target_arch.ARM,
                  target_bits = 64,
                  target_platform = builder_config.target_platform.CHROMEOS,
                  target_cros_boards = [
                      "fake-board1",
                      "fake-board2",
                  ],
                  cros_boards_with_qemu_images = [
                      "fake-board1",
                      "fake-board2",
                  ],
              ),
              android_config = builder_config.android_config(
                  config = "android-config1",
                  apply_configs = [
                      "android-config2",
                      "android-config3",
                  ],
              ),
              android_version_file = "//android/version/file",
              clobber = True,
              build_gs_bucket = "build-gs-bucket",
              run_tests_serially = True,
              perf_isolate_upload = True,
              expose_trigger_properties = True,
              skylab_upload_location = builder_config.skylab_upload_location(
                  gs_bucket = "skylab-gs-bucket"
                  gs_extra = "skylab-gs-extra"
              ),
              clusterfuzz_archive = builder_config.clusterfuzz_archive(
                  gs_bucket = "clusterfuzz-gs-bucket",
                  gs_acl = "clusterfuzz-gs-acl",
                  archive_name_prefix = "clusterfuzz-archive-name-prefix",
                  archive_subdir = "clusterfuzz-archive-subdir",
              ),
          ),

      foo-group:foo-tester
          builder_spec = builder_config.builder_spec(
              execution_mode = builder_config.execution_mode.TEST,
              gclient_config = builder_config.gclient_config(
                  config = "chromium",
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium",
              ),
          ),

      try-group:try-builder
          mirrors = [
              "ci/foo-builder",
              "ci/foo-tester",
              "ci/bar-builder",
          ],
          try_settings = builder_config.try_settings(
              include_all_triggered_testers = True,
              is_compile_only = True,
              analyze_names = [
                  "analyze-name1",
                  "analyze-name2",
              ],
              retry_failed_shards = False,
              retry_without_patch = False,
              rts_config = builder_config.rts_config(
                  condition = builder_config.rts_condition.QUICK_RUN_ONLY,
                  recall = 0.5,
              ),
          ),
      """)

  yield api.test(
      'migration',
      api.properties(
          migration_operation={
              'builders_to_migrate': [{
                  'builder_group': 'foo-group',
                  'builder': 'foo-builder',
              }],
              'output_path': '/fake/output/path',
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'foo-group': {
                  # This spec has nonsensical combinations, it provides coverage
                  # of the handling for different fields
                  'foo-builder':
                      ctbc.BuilderSpec.create(
                          gclient_config='gclient-config1',
                          gclient_apply_config=[
                              'gclient-config2',
                              'gclient-config3',
                          ],
                          chromium_config='chromium-config1',
                          chromium_apply_config=[
                              'chromium-config2',
                              'chromium-config3',
                          ],
                          chromium_config_kwargs={
                              'BUILD_CONFIG':
                                  'Release',
                              'TARGET_ARCH':
                                  'arm',
                              'TARGET_BITS':
                                  64,
                              'TARGET_PLATFORM':
                                  'chromeos',
                              'TARGET_CROS_BOARDS':
                                  'fake-board1:fake-board2',
                              'CROS_BOARDS_WITH_QEMU_IMAGES':
                                  'fake-board1:fake-board2',
                          },
                          android_config='android-config1',
                          android_apply_config=[
                              'android-config2',
                              'android-config3',
                          ],
                          android_version='//android/version/file',
                          clobber=True,
                          build_gs_bucket='build-gs-bucket',
                          serialize_tests=True,
                          perf_isolate_upload=True,
                          expose_trigger_properties=True,
                          skylab_gs_bucket='skylab-gs-bucket',
                          skylab_gs_extra='skylab-gs-extra',
                          cf_archive_build=True,
                          cf_gs_bucket="clusterfuzz-gs-bucket",
                          cf_gs_acl="clusterfuzz-gs-acl",
                          cf_archive_name="clusterfuzz-archive-name-prefix",
                          cf_archive_subdir_suffix="clusterfuzz-archive-subdir",
                      ),
                  'foo-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='foo-builder',
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
              },
              'bar-group': {
                  'bar-builder':
                      ctbc.BuilderSpec.create(
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
                  'bar-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='bar-builder',
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
              }
          }),
          ctbc.TryDatabase.create({
              'try-group': {
                  'try-builder':
                      ctbc.TrySpec.create(
                          mirrors=[
                              ctbc.TryMirror.create(
                                  builder_group='foo-group',
                                  buildername='foo-builder',
                                  tester='foo-tester',
                              ),
                              ctbc.TryMirror.create(
                                  builder_group='bar-group',
                                  buildername='bar-builder',
                              ),
                          ],
                          include_all_triggered_testers=True,
                          is_compile_only=True,
                          analyze_names=[
                              'analyze-name1',
                              'analyze-name2',
                          ],
                          retry_failed_shards=False,
                          retry_without_patch=False,
                          regression_test_selection=ctbc.QUICK_RUN_ONLY,
                          regression_test_selection_recall=0.5,
                      ),
              },
          }),
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_check(lambda check, steps: \
          check(expected_snippets in steps['src-side snippets'].cmd)),
      api.post_process(post_process.DropExpectation),
  )

  expected_standalone_snippet = textwrap.dedent("""\
      try-group:try-builder
          builder_spec = builder_config.builder_spec(
              gclient_config = builder_config.gclient_config(
                  config = "gclient-config",
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium-config",
              ),
          ),
          try_settings = builder_config.try_settings(
              retry_failed_shards = False,
          ),
      """)

  yield api.test(
      'migration-standalone-try-builder',
      api.properties(
          migration_operation={
              'builders_to_migrate': [{
                  'builder_group': 'try-group',
                  'builder': 'try-builder',
              }],
              'output_path': '/fake/output/path',
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'try-group': {
                  'try-builder':
                      ctbc.BuilderSpec.create(
                          gclient_config='gclient-config',
                          chromium_config='chromium-config',
                      ),
              },
          }),
          ctbc.TryDatabase.create({
              'try-group': {
                  'try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='try-group',
                          buildername='try-builder',
                          retry_failed_shards=False,
                      ),
              },
          }),
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_check(lambda check, steps: \
          check(expected_standalone_snippet in steps['src-side snippets'].cmd)),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'migration-unknown-builder',
      api.properties(
          migration_operation={
              'builders_to_migrate': [{
                  'builder_group': 'foo-group',
                  'builder': 'foo-builder',
              }],
              'output_path': '/fake/output/path',
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'bar-group': {
                  'bar-builder': ctbc.BuilderSpec.create(),
              },
          }),
          ctbc.TryDatabase.create({}),
      ),
      api.post_check(post_process.StatusException),
      api.post_check(post_process.ResultReason,
                     "unknown builder 'foo-group:foo-builder'"),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'migration-unsupported-attrs',
      api.properties(
          migration_operation={
              'builders_to_migrate': [{
                  'builder_group': 'foo-group',
                  'builder': 'foo-builder',
              }],
              'output_path': '/fake/output/path',
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'foo-group': {
                  'foo-builder':
                      ctbc.BuilderSpec.create(
                          bisect_archive_build=True,
                          bisect_gs_bucket='fake-bisect-gs-bucket',
                          bisect_gs_extra='fake-bisect-gs-extra',
                      ),
              }
          }),
          ctbc.TryDatabase.create({}),
      ),
      api.post_check(post_process.StatusException),
      api.post_check(
          post_process.ResultReasonRE,
          textwrap.dedent("""\
              \s*cannot migrate builder 'foo-group:foo-builder' with the \
following unsupported attrs:
              \s*\\* bisect_archive_build
              \s*\\* bisect_gs_bucket
              \s*\\* bisect_gs_extra""")),
      api.post_process(post_process.DropExpectation),
  )
