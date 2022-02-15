# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Utilities for handling the chromium_tests_builder_config properties.

This module contains two functions: validate and convert.

Validate takes a proto message object and runs any registered validator
function for the proto message. A list of strings containing validation
errors will be returned. There are validators registered for
InputProperties and all messages that can appear within InputProperties.

Convert takes a proto message object and kwargs containing any
additional information necessary for conversion and runs the registered
converted function for the proto message. An object representing the
same conceptual value will be returned. Converters are registered for
the following types with the specified additional keyword arguments:
* BuilderConfig
* BuilderDatabase
  * builder_id_by_builder_key - A mapping from (project, bucket,
    builder) to chromium.BuilderId. This allows for converting the proto
    message BuilderID to the in-memory BuilderId, which uses the builder
    group instead of the project and bucket.
* BuilderSpec
  * luci_project - The LUCI project to set for the BuilderSpec.
  * builder_id_by_builder_key - A mapping from (project, bucket,
    builder) to chromium.BuilderId. This allows for converting the proto
    message BuilderID to the in-memory BuilderId, which uses the builder
    group instead of the project and bucket.
"""

import collections

from RECIPE_MODULES.build.chromium import BuilderId
from RECIPE_MODULES.build import proto_validation

from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb
from PB.recipe_modules.build.chromium_tests_builder_config import (properties as
                                                                   properties_pb
                                                                  )

from . import (BuilderConfig, BuilderDatabase, BuilderSpec, COMPILE_AND_TEST,
               TEST, PROVIDE_TEST_SPEC, NEVER, QUICK_RUN_ONLY, ALWAYS)

VALIDATORS = proto_validation.Registry()


def _builder_key(builder_id):
  return (builder_id.project, builder_id.bucket, builder_id.builder)


@VALIDATORS.register(builder_pb.BuilderID)
def _validate_builder_id(obj, ctx):
  ctx.validate_field(obj, 'project')
  ctx.validate_field(obj, 'bucket')
  ctx.validate_field(obj, 'builder')


@VALIDATORS.register(properties_pb.BuilderSpec.LegacyGclientRecipeModuleConfig)
def _validate_legacy_gclient_recipe_module_config(obj, ctx):
  ctx.validate_field(obj, 'config')


@VALIDATORS.register(properties_pb.BuilderSpec.LegacyChromiumRecipeModuleConfig)
def _validate_legacy_chromium_recipe_module_config(obj, ctx):
  ctx.validate_field(obj, 'config')


@VALIDATORS.register(properties_pb.BuilderSpec.LegacyAndroidRecipeModuleConfig)
def _validate_legacy_android_recipe_module_config(obj, ctx):
  ctx.validate_field(obj, 'config')


@VALIDATORS.register(
    properties_pb.BuilderSpec.LegacyTestResultsRecipeModuleConfig)
def _validate_legacy_test_results_recipe_module_config(obj, ctx):
  ctx.validate_field(obj, 'config')


@VALIDATORS.register(properties_pb.BuilderSpec.SkylabUploadLocation)
def _validate_skylab_upload_location(obj, ctx):
  ctx.validate_field(obj, 'gs_bucket')


@VALIDATORS.register(properties_pb.BuilderSpec)
def _validate_builder_spec(obj, ctx):
  ctx.validate_field(obj, 'builder_group')
  ctx.validate_field(obj, 'execution_mode')
  ctx.validate_field(obj, 'legacy_gclient_config')
  ctx.validate_field(obj, 'legacy_chromium_config')
  ctx.validate_field(obj, 'legacy_android_config', optional=True)
  ctx.validate_field(obj, 'legacy_test_results_config', optional=True)
  ctx.validate_field(obj, 'skylab_upload_location', optional=True)


_EXECUTION_MODE_MAP = {
    properties_pb.BuilderSpec.ExecutionMode.COMPILE_AND_TEST:
        COMPILE_AND_TEST,
    properties_pb.BuilderSpec.ExecutionMode.TEST:
        TEST,
    properties_pb.BuilderSpec.ExecutionMode.PROVIDE_TEST_SPEC:
        PROVIDE_TEST_SPEC,
}


def _convert_builder_spec(obj, luci_project, builder_id_by_builder_key):
  parent_id = builder_id_by_builder_key.get(_builder_key(obj.parent))

  legacy_chromium_config = obj.legacy_chromium_config
  chromium_config_kwargs = {}
  for a in (
      'build_config',
      'target_arch',
      'target_bits',
      'target_platform',
  ):
    if legacy_chromium_config.HasField(a):
      chromium_config_kwargs[a.upper()] = getattr(legacy_chromium_config, a)
  for a in (
      'target_cros_boards',
      'cros_boards_with_qemu_images',
  ):
    val = getattr(legacy_chromium_config, a)
    if val:
      chromium_config_kwargs[a.upper()] = ':'.join(val)

  return BuilderSpec.create(
      luci_project=luci_project,
      execution_mode=_EXECUTION_MODE_MAP[obj.execution_mode],
      parent_builder_group=parent_id.group if parent_id else None,
      parent_buildername=parent_id.builder if parent_id else None,
      gclient_config=obj.legacy_gclient_config.config,
      gclient_apply_config=obj.legacy_gclient_config.apply_configs,
      chromium_config=legacy_chromium_config.config,
      chromium_apply_config=legacy_chromium_config.apply_configs,
      chromium_config_kwargs=chromium_config_kwargs,
      android_config=obj.legacy_android_config.config or None,
      android_apply_config=obj.legacy_android_config.apply_configs,
      test_results_config=obj.legacy_test_results_config.config or None,
      android_version=obj.android_version_file or None,
      clobber=obj.clobber,
      build_gs_bucket=obj.build_gs_bucket or None,
      serialize_tests=obj.run_tests_serially,
      expose_trigger_properties=obj.expose_trigger_properties,
      skylab_gs_bucket=obj.skylab_upload_location.gs_bucket or None,
      skylab_gs_extra=obj.skylab_upload_location.gs_extra or None,
  )


@VALIDATORS.register(properties_pb.BuilderDatabase.Entry)
def _validate_builder_database_entry(obj, ctx):
  ctx.validate_field(obj, 'builder_id')
  ctx.validate_field(obj, 'builder_spec')


@VALIDATORS.register(properties_pb.BuilderDatabase)
def _validate_builder_database(obj, ctx):
  location_by_builder_key = {}

  def check_builder_id_unique(entry, sub_ctx):
    builder_key = _builder_key(entry.builder_id)
    if builder_key in location_by_builder_key:
      sub_ctx.error('{}.builder_id is the same as {}.builder_id'.format(
          sub_ctx.location, location_by_builder_key[builder_key]))
    else:
      location_by_builder_key[builder_key] = sub_ctx.location

  ctx.validate_repeated_field(obj, 'entries', callback=check_builder_id_unique)


def _convert_builder_database(obj, builder_id_by_builder_key):
  builders = collections.defaultdict(dict)
  for entry in obj.entries:
    builder_id = builder_id_by_builder_key[_builder_key(entry.builder_id)]
    builders[builder_id.group][builder_id.builder] = _convert_builder_spec(
        entry.builder_spec,
        luci_project=entry.builder_id.project,
        builder_id_by_builder_key=builder_id_by_builder_key)
  return BuilderDatabase.create(builders)


@VALIDATORS.register(properties_pb.BuilderConfig.BuilderGroupAndName)
def _validate_builder_group_and_name(obj, ctx):
  ctx.validate_field(obj, 'group')
  ctx.validate_field(obj, 'builder')


@VALIDATORS.register(properties_pb.BuilderConfig.RtsConfig)
def _validate_rts_config(obj, ctx):
  ctx.validate_field(obj, 'condition')


@VALIDATORS.register(properties_pb.BuilderConfig)
def _validate_builder_config(obj, ctx):
  builders = set(_builder_key(e.builder_id) for e in obj.builder_db.entries)

  def check_builder_id_in_db(builder_id, sub_ctx):
    if _builder_key(builder_id) not in builders:
      sub_ctx.error('there is no entry in {}.builder_db for {}'.format(
          ctx.location, sub_ctx.location))

  ctx.validate_field(obj, 'builder_db')
  ctx.validate_repeated_field(
      obj, 'builder_ids', callback=check_builder_id_in_db)
  ctx.validate_repeated_field(
      obj,
      'builder_ids_in_scope_for_testing',
      optional=True,
      callback=check_builder_id_in_db)
  ctx.validate_repeated_field(
      obj, 'mirroring_builder_group_and_names', optional=True)
  ctx.validate_field(obj, 'rts_config', optional=True)


_RTS_CONDITION_MAP = {
    properties_pb.BuilderConfig.RtsConfig.Condition.NEVER:
        NEVER,
    properties_pb.BuilderConfig.RtsConfig.Condition.QUICK_RUN_ONLY:
        QUICK_RUN_ONLY,
    properties_pb.BuilderConfig.RtsConfig.Condition.ALWAYS:
        ALWAYS,
}


def convert_builder_config(obj):
  # The builder ID in the protos is (project, bucket, builder), whereas the
  # one in the recipes is (group, builder), so we need to map between them
  # until such time as the recipes version uses project and bucket
  builder_id_by_builder_key = {
      _builder_key(entry.builder_id):
      BuilderId.create_for_group(entry.builder_spec.builder_group,
                                 entry.builder_id.builder)
      for entry in obj.builder_db.entries
  }

  rts_condition = obj.rts_config and obj.rts_config.condition or None
  regression_test_selection = (
      _RTS_CONDITION_MAP[rts_condition] if rts_condition is not None else None)

  return BuilderConfig.create(
      builder_db=_convert_builder_database(
          obj.builder_db, builder_id_by_builder_key=builder_id_by_builder_key),
      builder_ids=[
          builder_id_by_builder_key[_builder_key(b)] for b in obj.builder_ids
      ],
      builder_ids_in_scope_for_testing=[
          builder_id_by_builder_key[_builder_key(b)]
          for b in obj.builder_ids_in_scope_for_testing
      ],
      mirroring_try_builders=[
          BuilderId.create_for_group(x.group, x.builder)
          for x in obj.mirroring_builder_group_and_names
      ],
      include_all_triggered_testers=False,
      is_compile_only=obj.is_compile_only,
      analyze_names=obj.analyze_names,
      retry_failed_shards=(obj.retry_failed_shards
                           if obj.HasField('retry_failed_shards') else True),
      retry_without_patch=(obj.retry_without_patch
                           if obj.HasField('retry_without_patch') else True),
      regression_test_selection=regression_test_selection,
      regression_test_selection_recall=obj.rts_config.recall or None,
  )


@VALIDATORS.register(properties_pb.InputProperties)
def _validate_input_properties(obj, ctx):
  ctx.validate_field(obj, 'builder_config', optional=True)
