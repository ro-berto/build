# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import six

from recipe_engine import recipe_test_api

from RECIPE_MODULES.build.attr_utils import attrs, attrib, enum
from RECIPE_MODULES.build.chromium import BuilderId

from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb
from PB.recipe_modules.build.chromium_tests_builder_config import (properties as
                                                                   properties_pb
                                                                  )

from . import (builders, trybots, BuilderConfig, BuilderDatabase, BuilderSpec,
               TryDatabase)

_DEFAULT_SPEC = BuilderSpec.create(
    gclient_config='chromium',
    chromium_config='chromium',
)

_ExecutionMode = properties_pb.BuilderSpec.ExecutionMode


@attrs()
class BuilderDetails(object):
  """Details for specifying builders in properties.

  The following fields can be set by the caller when using the
  properties assemblers:
  * project - The LUCI project of the builder.
  * bucket - The LUCI bucket of the builder. A default will be set by
    the properties assemblers methods.
  * builder - The name of the builder.
  * builder_group - The builder group of the builder.
  * builder_spec - The builder spec that should be produced for the
    builder when converting the properties to in-memory representations.
    The execution_mode, parent_builder_group and parent_buildername
    attributes will be ignored and set appropriately based on the method
    that is adding the builder.
  """

  project = attrib(str, default='chromium')
  bucket = attrib(str)
  builder = attrib(str)
  builder_group = attrib(str)
  builder_spec = attrib(BuilderSpec, default=_DEFAULT_SPEC)

  # Private fields, controlled by the properties assemblers and cannot be
  # set by the caller
  execution_mode = attrib(enum(_ExecutionMode.values()))
  parent = attrib(builder_pb.BuilderID, default=None)


class _PropertiesAssembler(object):

  def __init__(self):
    self._builder_entries = []
    self._builder_ids = []
    self._builder_ids_in_scope_for_testing = []

  def assemble(self):
    return properties_pb.InputProperties(
        builder_config=properties_pb.BuilderConfig(
            builder_db=properties_pb.BuilderDatabase(
                entries=self._builder_entries),
            builder_ids=self._builder_ids,
            builder_ids_in_scope_for_testing=(
                self._builder_ids_in_scope_for_testing),
        ))

  def add_builder(self, details):
    builder_id = builder_pb.BuilderID(
        project=details.project,
        bucket=details.bucket,
        builder=details.builder,
    )

    builder_spec = self._get_builder_spec(details)

    self._builder_entries.append(
        properties_pb.BuilderDatabase.Entry(
            builder_id=builder_id,
            builder_spec=builder_spec,
        ))

    return builder_id

  def add_builder_id(self, builder_id):
    self._builder_ids.append(builder_id)

  def add_builder_id_in_scope_for_testing(self, builder_id):
    self._builder_ids_in_scope_for_testing.append(builder_id)

  def _get_builder_spec(self, details):
    builder_spec = details.builder_spec

    kwargs = {
        'builder_group':
            details.builder_group,
        'execution_mode':
            details.execution_mode,
        'parent':
            details.parent,
        'legacy_gclient_config':
            self._get_legacy_gclient_config(builder_spec),
        'legacy_chromium_config':
            self._get_legacy_chromium_config(builder_spec),
        'legacy_android_config':
            self._get_legacy_android_config(builder_spec),
        'legacy_test_results_config':
            self._get_legacy_test_results_config(builder_spec),
        'android_version_file':
            builder_spec.android_version,
        'clobber':
            builder_spec.clobber,
        'build_gs_bucket':
            builder_spec.build_gs_bucket,
        'run_tests_serially':
            builder_spec.serialize_tests,
        'expose_trigger_properties':
            builder_spec.expose_trigger_properties,
        'skylab_upload_location':
            self._get_skylab_upload_location(builder_spec),
    }

    return properties_pb.BuilderSpec(
        **{k: v for k, v in six.iteritems(kwargs) if v is not None})

  @staticmethod
  def _get_legacy_gclient_config(builder_spec):
    return properties_pb.BuilderSpec.LegacyGclientRecipeModuleConfig(
        config=builder_spec.gclient_config,
        apply_configs=builder_spec.gclient_apply_config,
    )

  @staticmethod
  def _get_legacy_chromium_config(builder_spec):
    kwargs = {
        'config': builder_spec.chromium_config,
        'apply_configs': builder_spec.chromium_apply_config,
    }
    for a in (
        'BUILD_CONFIG',
        'TARGET_ARCH',
        'TARGET_BITS',
        'TARGET_PLATFORM',
    ):
      if a in builder_spec.chromium_config_kwargs:
        kwargs[a.lower()] = (builder_spec.chromium_config_kwargs[a])
    for a in (
        'TARGET_CROS_BOARDS',
        'CROS_BOARDS_WITH_QEMU_IMAGES',
    ):
      if a in builder_spec.chromium_config_kwargs:
        kwargs[a.lower()] = (builder_spec.chromium_config_kwargs[a].split(':'))
    return properties_pb.BuilderSpec.LegacyChromiumRecipeModuleConfig(**kwargs)

  @staticmethod
  def _get_legacy_android_config(builder_spec):
    kwargs = {}
    if builder_spec.android_config is not None:
      kwargs['config'] = builder_spec.android_config
    if builder_spec.android_apply_config:
      kwargs['apply_configs'] = builder_spec.android_apply_config
    if kwargs:
      return properties_pb.BuilderSpec.LegacyAndroidRecipeModuleConfig(**kwargs)
    return None

  @staticmethod
  def _get_legacy_test_results_config(builder_spec):
    kwargs = {}
    if builder_spec.test_results_config is not None:
      kwargs['config'] = builder_spec.test_results_config
    if kwargs:
      return properties_pb.BuilderSpec.LegacyTestResultsRecipeModuleConfig(
          **kwargs)
    return None

  @staticmethod
  def _get_skylab_upload_location(builder_spec):
    kwargs = {}
    for (src, dst) in (
        ('skylab_gs_bucket', 'gs_bucket'),
        ('skylab_gs_extra', 'gs_extra'),
    ):
      val = getattr(builder_spec, src)
      if val is not None:
        kwargs[dst] = val
    if kwargs:
      return properties_pb.BuilderSpec.SkylabUploadLocation(**kwargs)
    return None


class _CiBuilderPropertiesAssembler(object):

  def __init__(self, props_assembler, builder_id, builder_spec):
    self._props_assembler = props_assembler
    self._builder_id = builder_id
    self._builder_spec = builder_spec

  @classmethod
  def create(cls, **kwargs):
    props_assembler = _PropertiesAssembler()
    kwargs.setdefault('bucket', 'ci')
    details = BuilderDetails(
        execution_mode=_ExecutionMode.COMPILE_AND_TEST, parent=None, **kwargs)
    builder_id = props_assembler.add_builder(details)
    props_assembler.add_builder_id(builder_id)
    return cls(props_assembler, builder_id, details.builder_spec)

  def with_tester(self, **kwargs):
    kwargs.setdefault('builder_spec', self._builder_spec)
    kwargs.setdefault('bucket', 'ci')
    details = BuilderDetails(
        execution_mode=_ExecutionMode.TEST, parent=self._builder_id, **kwargs)
    tester_id = self._props_assembler.add_builder(details)
    self._props_assembler.add_builder_id_in_scope_for_testing(tester_id)
    return self

  def assemble(self):
    return self._props_assembler.assemble()


class _CiTesterPropertiesAssembler(object):

  def __init__(self, props_assembler, tester_details):
    self._props_assembler = props_assembler
    self._tester_details = tester_details
    self._parent_details = None

  @classmethod
  def create(cls, **kwargs):
    props_assembler = _PropertiesAssembler()
    kwargs.setdefault('bucket', 'ci')
    details = BuilderDetails(execution_mode=_ExecutionMode.TEST, **kwargs)
    return cls(props_assembler, details)

  def with_parent(self, **kwargs):
    if self._parent_details is not None:
      raise TypeError('`with_parent` can only be called once')

    kwargs.setdefault('builder_spec', self._tester_details.builder_spec)
    kwargs.setdefault('bucket', 'ci')
    details = BuilderDetails(
        execution_mode=_ExecutionMode.COMPILE_AND_TEST, **kwargs)
    builder_id = self._props_assembler.add_builder(details)
    self._parent_details = details

    tester_details = attr.evolve(self._tester_details, parent=builder_id)
    tester_id = self._props_assembler.add_builder(tester_details)

    self._props_assembler.add_builder_id(tester_id)

    return self

  def assemble(self):
    if self._parent_details is None:
      raise TypeError('`with_parent` must be called before calling `assemble`')
    return self._props_assembler.assemble()


class _TryBuilderPropertiesAssembler(object):

  def __init__(self, props_assembler):
    self._props_assembler = props_assembler
    # ID and spec of the most recently added builder
    self._builder_id = None
    self._builder_spec = None

  # TODO(gbeaty) Update this to accept arguments for changing the try settings
  # (retry shards, RTS, etc.)
  @classmethod
  def create(cls):
    props_assembler = _PropertiesAssembler()
    return cls(props_assembler)

  def with_mirrored_builder(self, **kwargs):
    kwargs.setdefault('bucket', 'ci')
    kwargs.setdefault('builder_spec', self._builder_spec)
    details = BuilderDetails(
        execution_mode=_ExecutionMode.COMPILE_AND_TEST, parent=None, **kwargs)

    builder_id = self._props_assembler.add_builder(details)
    self._props_assembler.add_builder_id(builder_id)

    self._builder_id = builder_id
    self._builder_spec = details.builder_spec

    return self

  def with_mirrored_tester(self, **kwargs):
    if self._builder_id is None:
      raise TypeError('`with_mirrored_builder` must be called'
                      ' before calling `with_mirrored_tester`')

    kwargs.setdefault('bucket', 'ci')
    kwargs.setdefault('builder_spec', self._builder_spec)
    details = BuilderDetails(
        execution_mode=_ExecutionMode.TEST, parent=self._builder_id, **kwargs)

    tester_id = self._props_assembler.add_builder(details)
    self._props_assembler.add_builder_id_in_scope_for_testing(tester_id)

    return self

  def assemble(self):
    if self._builder_id is None:
      raise TypeError(
          '`with_mirrored_builder` must be called before calling `assemble`')
    return self._props_assembler.assemble()


class ChromiumTestsBuilderConfigApi(recipe_test_api.RecipeTestApi):

  def properties(self, properties):
    assert isinstance(properties, properties_pb.InputProperties)
    return self.m.properties(
        **{'$build/chromium_tests_builder_config': properties})

  @staticmethod
  def properties_assembler_for_ci_builder(**kwargs):
    """Get a properties assembler for a CI builder.

    See BuilderDetails for information on the allowed keyword arguments.
    The value of bucket will default to 'ci'.

    The returned object has 2 methods:
    * with_tester - Adds a tester to the properties with the CI builder
      as its parent. If `builder_spec` is not specified, it will use the
      value specified for the CI builder, if any. This can be called
      multiple times before calling `assemble`.
    * assemble - Creates the proto properties object for the module.
    """
    return _CiBuilderPropertiesAssembler.create(**kwargs)

  @staticmethod
  def properties_assembler_for_ci_tester(**kwargs):
    """Get a properties assembler for a CI tester.

    See BuilderDetails for information on the allowed keyword arguments.
    The value of bucket will default to 'ci'.

    The returned object has 2 methods:
    * with_parent - Adds the parent builder for the tester. If
      `builder_spec` is not specified, it will use the value specified
      for the CI tester, if any. This must be called exactly once before
      calling `assemble`.
    * assemble - Creates the proto properties object for the module. It is
      an error to call this before calling `with_parent`.
    """
    return _CiTesterPropertiesAssembler.create(**kwargs)

  @staticmethod
  def properties_assembler_for_try_builder():
    """Get a properties assembler for a try builder.

    The returned object has 3 methods:
    * with_mirrored_builder - Adds a builder that the try builder
      mirrors. If `builder_spec` is not specified, it will use the last
      specified builder spec. Must be called at least once with
      `builder_spec` set.
    * with_mirrored_tester - Adds a tester with the most recently
      mirrored builder as the parent. If `builder_spec` is not
      specified, it will use the parent's builder spec.
      `with_mirrored_builder` must be called at least once before
      calling this.
    * assemble - Creates the proto properties object for the module. It
      is an error to call this before calling `with_mirrored_builder`.
    """
    return _TryBuilderPropertiesAssembler.create()

  @staticmethod
  def _get_builder_id(builder_group, builder, **_):
    return BuilderId.create_for_group(builder_group, builder)

  # TODO(gbeaty) After migration to python3 is complete, change the signature to
  # (*, use_try_db, builder_db=None, try_db=None)
  @staticmethod
  def _get_databases(use_try_db, **kwargs):
    if 'builder_db' in kwargs:
      builder_db = kwargs.pop('builder_db')
      if use_try_db:
        assert 'try_db' in kwargs, (
            'If using try_db, '
            'try_db must be specified when specifying builder_db')
      try_db = kwargs.pop('try_db', None) or TryDatabase.create({})

    else:
      assert not 'try_db' in kwargs, (
          'Cannot specify try_db without specifying builder_db')
      builder_db = builders.BUILDERS
      try_db = trybots.TRYBOTS

    return builder_db, try_db, use_try_db, kwargs

  # TODO(gbeaty) After migration to python3 is complete, change the signature to
  # (*, builder_group, builder, use_try_db, builder_db=None, try_db=None)
  def _test_data(self, **kwargs):
    builder_id = self._get_builder_id(**kwargs)
    builder_db, try_db, use_try_db, kwargs = self._get_databases(**kwargs)

    builder_config = BuilderConfig.lookup(builder_id, builder_db,
                                          try_db if use_try_db else None)

    test_data = sum([
        self.databases(builder_db, try_db),
        self.m.platform(
            builder_config.simulation_platform or 'linux',
            builder_config.chromium_config_kwargs.get('TARGET_BITS', 64)),
    ], self.empty_test_data())

    return test_data, kwargs

  def generic_build(self, **kwargs):
    """Create test data for a generic build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium and
    chromium_tests_builder_config modules for builds that have neither
    an associated gitiles commit or gerrit change (e.g. CI builder
    triggered via the scheduler UI or a cron-like schedule).

    All keyword arguments supported by chromium.generic_build are
    supported, as well as the following additional keyword arguments:
    * builder_db - Overrides the default builder database.
    * try_db - Override the default try database. Can only be specified
      if builder_db is also specified. If builder_db is specified and
      try_db is not specified, an empty try database will be used as the
      default try database.
    * use_try_db - Whether the try_db should be used for looking up the
      builder to set the platform.
    """
    kwargs.setdefault('builder', 'Linux Builder')
    kwargs.setdefault('builder_group', 'chromium.linux')
    kwargs.setdefault('use_try_db', False)
    ctbc_test_data, kwargs = self._test_data(**kwargs)
    return self.m.chromium.generic_build(**kwargs) + ctbc_test_data

  def ci_build(self, **kwargs):
    """Create test data for a CI build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium and
    chromium_tests_builder_config modules for builds that would be
    triggered by a scheduler poller with an associated gitiles commit
    (or triggered by another builder that was triggered by a scheduler
    poller).

    All keyword arguments supported by chromium.generic_build are
    supported, as well as the following additional keyword arguments:
    * builder_db - Overrides the default builder database.
    * try_db - Override the default try database. Can only be specified
      if builder_db is also specified. If builder_db is specified and
      try_db is not specified, an empty try database will be used as the
      default try database.
    """
    assert 'use_try_db' not in kwargs
    kwargs.setdefault('builder', 'Linux Builder')
    kwargs.setdefault('builder_group', 'chromium.linux')
    ctbc_test_data, kwargs = self._test_data(use_try_db=False, **kwargs)
    return self.m.chromium.ci_build(**kwargs) + ctbc_test_data

  def try_build(self, **kwargs):
    """Create test data for a try build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium and
    chromium_tests_builder_config modules for try builds with an
    associated gerrit change.

    All keyword arguments supported by chromium.generic_build are
    supported, as well as the following additional keyword arguments:
    * builder_db - Overrides the default builder database.
    * try_db - Override the default try database. Can only be specified
      if builder_db is also specified. If builder_db is specified and
      try_db is not specified, an empty try database will be used as the
      default try database.
    """
    assert 'use_try_db' not in kwargs
    kwargs.setdefault('builder', 'linux-rel')
    kwargs.setdefault('builder_group', 'tryserver.chromium.linux')
    ctbc_test_data, kwargs = self._test_data(use_try_db=True, **kwargs)
    return self.m.chromium.try_build(**kwargs) + ctbc_test_data

  # TODO(https://crbug.com/1193832) Switch callers to use (generic|ci|try)_build
  @recipe_test_api.mod_test_data
  @staticmethod
  def databases(builder_db, try_db=None):
    """Override the default BuilderDatabase and TryDatabase for a test.

    Generally (generic|ci|try)_build should be preferred instead, use
    this only for tests of recipes that directly access
    chromium_tests_builder_config.builder_db and/or lookup a builder
    other than the "current" builder.

    Args:
      * builder_db - A BuilderDatabase to replace
        chromium_tests_builder_config.builder_db.
      * try_db - A TryDatabase to replace
        chromium_tests_builder_config.try_db. All builder IDs present in
        the contained try specs must be present in `builder_db`.
    """
    assert isinstance(builder_db, BuilderDatabase)
    assert try_db is None or isinstance(try_db, TryDatabase)
    return builder_db, try_db
