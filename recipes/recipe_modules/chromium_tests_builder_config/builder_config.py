# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import traceback

from .builder_db import BuilderDatabase
from .try_spec import TryDatabase, TrySpec, COMPILE

from RECIPE_MODULES.build.attr_utils import attrib, attrs, cached_property


class BuilderConfigException(Exception):
  """Exception indicating an attempt to create an invalid BuilderConfig."""
  pass


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
  try_db = attrib(TryDatabase, default=TryDatabase.create({}))
  _try_spec = attrib(TrySpec)

  @classmethod
  def create(cls, builder_db, try_spec, try_db=None, python_api=None):
    """Create a BuilderConfig instance.

    Args:
      * builder_db - The BuilderDatabase containing the builders of
        try_spec.mirrors.
      * try_spec - A TrySpec instance that specifies the builders to
        mirror and any try-specific settings.
      * python_api - Optional python API. If provided, in the event that
        a BuilderConfigException would be raised, an infra failing step
        will be created with the details instead.

    Returns:
      A BuilderConfig instance. The BuilderConfig will wrap the
      specs for the builders in the mirrors in `try_spec`. The testers
      in the mirrors in `try_spec` will be in scope for testing. If
      `try_spec.include_all_triggered_testers` is true, then any testers
      triggered by the wrapped builders will be in scope for testing.

    Raises:
      * BuilderConfigException if there isn't configuration matching all
        of builders in try_spec.mirrors and python_api is None.
      * InfraFailure if there isn't configuration matching all of
        builders in try_spec.mirrors and python_api is not None.
    """
    try:
      return cls(builder_db, try_db, try_spec)
    except BuilderConfigException as e:
      if python_api is not None:
        python_api.infra_failing_step(
            str(e), [traceback.format_exc()], as_log='details')
      raise

  def __attrs_post_init__(self):
    for mirror in self.mirrors:
      if not mirror.builder_id.group in self.builder_db.builders_by_group:
        raise BuilderConfigException(
            'No configuration present for group {!r}'.format(
                mirror.builder_id.group))
      if not mirror.builder_id in self.builder_db:
        raise BuilderConfigException(
            'No configuration present for builder {!r} in group {!r}'.format(
                mirror.builder_id.builder, mirror.builder_id.group))

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

    try_spec = None
    if use_try_db and try_db:
      try_spec = try_db.get(builder_id)

    # TODO(gbeaty) Change implementation to not require a TrySpec object
    # BuilderConfig is implemented in terms of TrySpec, so one gets created for
    # CI builders and stand-alone try builders that mirrors the indicated
    # builder and any trigger testers
    if try_spec is None:
      try_spec = TrySpec.create([builder_id],
                                include_all_triggered_testers=True)

    return cls.create(
        builder_db, try_db=try_db, try_spec=try_spec, python_api=python_api)

  def __getattr__(self, attr):
    per_builder_values = {}
    for builder_id in self.builder_ids:
      builder_spec = self.builder_db[builder_id]
      value = getattr(builder_spec, attr)
      per_builder_values[builder_id] = value
    values = list(set(per_builder_values.values()))
    assert len(values) == 1, 'Inconsistent value for {!r}:\n  {}'.format(
        attr, '\n  '.join('{!r}: {!r}'.format(k, v)
                          for k, v in per_builder_values.iteritems()))
    return values[0]

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
    if self._try_spec.include_all_triggered_testers:
      ids = self.builder_db.builder_graph.get_transitive_closure(ids)
    return ids

  @cached_property
  def mirrors(self):
    return self._try_spec.mirrors

  @cached_property
  def analyze_names(self):
    return self._try_spec.analyze_names

  @cached_property
  def retry_failed_shards(self):
    return self._try_spec.retry_failed_shards

  @cached_property
  def retry_without_patch(self):
    return self._try_spec.retry_without_patch

  @cached_property
  def is_compile_only(self):
    return self._try_spec.execution_mode == COMPILE

  @cached_property
  def regression_test_selection(self):
    return self._try_spec.regression_test_selection

  @cached_property
  def regression_test_selection_recall(self):
    return self._try_spec.regression_test_selection_recall

  @cached_property
  def source_side_spec_files(self):
    groups = set(builder_id.group
                 for builder_id in self.builder_ids_in_scope_for_testing)
    return {g: '{}.json'.format(g) for g in groups}
