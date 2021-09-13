# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import inspect
import six
import traceback

from .builder_spec import BuilderSpec
from .builder_db import BuilderDatabase
from .try_spec import TryDatabase, TryMirror, ALWAYS, NEVER, QUICK_RUN_ONLY

from RECIPE_MODULES.build.chromium import BuilderId
from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             enum, sequence)


class BuilderConfigException(Exception):
  """Exception indicating an attempt to create an invalid BuilderConfig."""
  pass


class _BuilderSpecProperty(object):
  """A non-data descriptor that delegates attributes to BuilderSpecs.

  This descriptor must be attached to the BuilderConfig class. The value
  for the attribute will be read from each of the BuilderSpecs that are
  wrapped by the BuilderConfig instance and an exception will be raised
  if there is more than one value.

  A descriptor is being used instead of overriding __getattr__ because
  the presence of a __getattr__ method on the type results in errors in
  property methods being hidden because python will fall back to calling
  __getattr__ if a property raises an exception.
  """

  def __init__(self, a):
    self._attr = a

  def __get__(self, obj, objtype=None):
    del objtype
    if obj is None:
      return self  # pragma: no cover
    per_builder_values = {}
    for builder_id in obj.builder_ids:
      builder_spec = obj.builder_db[builder_id]
      value = getattr(builder_spec, self._attr)
      per_builder_values[builder_id] = value
    values = list(set(per_builder_values.values()))
    if len(values) != 1:
      message = ['Inconsistent value for {!r}:'.format(self._attr)]
      message.extend(
          '{!r}: {!r}'.format(k, v) for k, v in per_builder_values.iteritems())
      raise ValueError('\n  '.join(message))
    return values[0]


def delegate_to_builder_spec(builder_spec_class):
  """A decorator to delegate attribute and property access to specs.

  The decorator can be applied to a BuilderConfig subclass and takes a
  BuilderSpec subclass. For each attr Attribute or descriptor on the
  class, if the attribute's name is not a python magic name (begins and
  ends with double-underscore), a non-data descriptor will be added to
  the BuilderConfig subclass that will delegate to the wrapped builder
  specs and ensure a consistent value between them.
  """
  assert issubclass(builder_spec_class, BuilderSpec)

  def delegate(cls):
    for a in attr.fields_dict(builder_spec_class):
      setattr(cls, a, _BuilderSpecProperty(a))
    for a in dir(builder_spec_class):
      if a.startswith('__') and a.endswith('__'):
        continue
      val = getattr(builder_spec_class, a)
      if inspect.ismethod(val):
        continue
      if hasattr(val, '__get__'):
        setattr(cls, a, _BuilderSpecProperty(a))
    return cls

  return delegate


@delegate_to_builder_spec(BuilderSpec)
@attrs()
class BuilderConfig(object):
  """"Static" configuration for a builder.

  BuilderConfig provides access to information defined entirely in
  recipes; for a given recipe version BuilderConfig information will be
  the same for all builds of a given builder.

  BuilderConfig wraps multiple builder specs and provides the means for
  getting values in a manner that ensures they are compatible between
  all of the wrapped specs. BuilderConfig overrides attribute access so
  that attempting to access any attribute that is defined on the specs
  returns the value on the specs, raising an exception if the value is
  inconsistent between the specs. The builders that have their specs
  wrapped are returned by `builder_ids`.

  In addition to wrapping the BuilderSpecs for some builders, it can
  also record other builders as being in scope for testing (e.g. a
  tester triggered by a builder whose spec is wrapped). The builders
  that are in scope for testing will not have their specs wrapped, but
  will have their source side spec files included when accessing
  `source_side_spec_files`.
  """

  builder_db = attrib(BuilderDatabase)

  # The try builders that mirror the builder that this BuilderConfig
  # wraps
  mirroring_try_builders = attrib(sequence[BuilderId], default=())

  # TODO(gbeaty) The following fields are copied from TrySpec (with some
  # changed defaults), but if all builders are switched to using the
  # module properties (once available) then TrySpec could be removed.

  # The specifications of the builders being mirrored by the try builder
  mirrors = attrib(sequence[TryMirror])
  # Whether or not all testers triggered by builders in mirrors should be
  # considered in scope for testing
  include_all_triggered_testers = attrib(bool, default=True)
  # Whether the try builder is compile only or not
  is_compile_only = attrib(bool, default=False)
  # Additional names to add when analyzing the change to determine affected
  # targets
  analyze_names = attrib(sequence[str], default=())
  # Whether or not failed shards of tests should be retried
  retry_failed_shards = attrib(bool, default=True)
  # Whether or not failed test suites should be retried without patch
  retry_without_patch = attrib(bool, default=True)
  # See http://bit.ly/chromium-rts
  regression_test_selection = attrib(
      enum([ALWAYS, QUICK_RUN_ONLY, NEVER]), default=NEVER)
  regression_test_selection_recall = attrib(float, default=0.95)

  @classmethod
  def create(cls, builder_db, mirrors, python_api=None, **kwargs):
    """Create a BuilderConfig instance.

    Args:
      * builder_db - The BuilderDatabase containing the builders of
        `mirrors`.
      * mirrors - A non-empty collection of BuilderId or TryMirror
        instances specifying the builders to wrap and those that in
        scope for testing. BuilderId instances will be normalized to
        TryMirror instances with builder_id set to the BuilderId.
      * python_api - Optional python API. If provided, in the event that
        a BuilderConfigException would be raised, an infra failing step
        will be created with the details instead.
      * kwargs - Any additional arguments to initialize fields of the
        BuilderConfig.

    Returns:
      A BuilderConfig instance. The BuilderConfig will wrap the specs
      for the builders in `mirrors`. The testers in `mirrors` will be in
      scope for testing. If `include_all_triggered_testers` is true,
      then any testers triggered by the wrapped builders will be in
      scope for testing.

    Raises:
      * BuilderConfigException if there isn't configuration matching all
        of builders in mirrors and python_api is None.
      * InfraFailure if there isn't configuration matching all of
        builders in mirrors and python_api is not None.
    """
    try:
      if not mirrors:
        raise BuilderConfigException('No mirrors specified')
      mirrors = [TryMirror.normalize(m) for m in mirrors]
      for mirror in mirrors:
        if not mirror.builder_id.group in builder_db.builders_by_group:
          raise BuilderConfigException(
              "No configuration present for group '{}'".format(
                  mirror.builder_id.group))
        if not mirror.builder_id in builder_db:
          raise BuilderConfigException(
              "No configuration present for builder '{}' in group '{}'".format(
                  mirror.builder_id.builder, mirror.builder_id.group))
    except BuilderConfigException as e:
      if python_api is not None:
        python_api.infra_failing_step(
            str(e), [traceback.format_exc()], as_log='details')
      raise

    return cls(builder_db, mirrors=mirrors, **kwargs)

  @classmethod
  def lookup(cls,
             builder_id,
             builder_db,
             try_db=None,
             use_try_db=True,
             python_api=None):
    """Create a BuilderConfig by looking up a builder.

    Args:
      * builder_id - The ID of the builder to look up.
      * builder_db - The BuilderDatabase that the builder will be looked
        up in.
      * try_db - An optional TryDatabase that the builder will be looked
        up in.
      * python_api - Optional python API. If provided, in the event that
        a BuilderConfigException would be raised, an infra failing step
        will be created with the details instead.

    Returns:
      A BuilderConfig instance for the associated builder. If try_db was
      provided and has an entry for the builder, the BuilderConfig will
      use the associated TrySpec, see the documentation for `create` for
      specific details. Otherwise, the BuilderConfig will wrap the
      builder spec for the provided builder ID and any triggered testers
      will be in scope for testing.

    Raises:
      * BuilderConfigException if there isn't configuration matching the
        indicated builder and python_api is None.
      * InfraFailure if there isn't configuration matching the indicated
        builder and python_api is not None.
    """
    assert isinstance(builder_db, BuilderDatabase), (
        'Expected BuilderDatabase for builder_db, got {}'.format(
            type(builder_db)))
    assert try_db is None or isinstance(try_db, TryDatabase), \
        'Expected TryDatabase for try_db, got {}'.format(type(try_db))

    kwargs = {}

    try_spec = None
    if try_db:
      if builder_id not in try_db:

        def is_builder_mirrored(spec):
          for mirror in spec.mirrors:
            if builder_id in (mirror.builder_id, mirror.tester_id):
              return True
          return False

        kwargs['mirroring_try_builders'] = [
            try_id for try_id, spec in six.iteritems(try_db)
            if is_builder_mirrored(spec)
        ]

      elif use_try_db:
        try_spec = try_db.get(builder_id)

    if try_spec is None:
      kwargs['mirrors'] = [builder_id]
    else:
      kwargs.update(attr.asdict(try_spec, recurse=False))

    return cls.create(builder_db, python_api=python_api, **kwargs)

  @cached_property
  def builder_ids(self):
    """The builder IDs that have their specs wrapped by this config."""
    return [m.builder_id for m in self.mirrors]

  @cached_property
  def builder_ids_in_scope_for_testing(self):
    """The builder IDs that tests and targets should be built for."""
    ids = list(self.builder_ids)
    ids.extend(mirror.tester_id
               for mirror in self.mirrors
               if mirror.tester_id is not None)
    if self.include_all_triggered_testers:
      ids = self.builder_db.builder_graph.get_transitive_closure(ids)
    return ids

  @cached_property
  def source_side_spec_files(self):
    groups = set(builder_id.group
                 for builder_id in self.builder_ids_in_scope_for_testing)
    return {g: '{}.json'.format(g) for g in groups}
