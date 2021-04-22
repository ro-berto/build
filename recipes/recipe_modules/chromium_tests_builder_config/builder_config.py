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
  """"Static" configuration for a bot.

  BuilderConfig provides access to information defined entirely in
  recipes; for a given recipe version BuilderConfig information will be
  the same for all builds of a given builder.

  BuilderConfig wraps multiple bot specs and provides the means for
  getting values in a manner that ensures they are compatible between
  all of the wrapped specs. BuilderConfig overrides attribute access so
  that attempting to access any attribute that is defined on the specs
  returns the value on the specs, raising an exception if the value is
  inconsistent between the specs.
  """

  builder_db = attrib(BuilderDatabase)
  _try_spec = attrib(TrySpec)

  @classmethod
  def create(cls, builder_db, try_spec, python_api=None):
    """Create a BuilderConfig instance.

    Args:
      * builder_db - The BuilderDatabase containing the builders of
        try_spec.mirrors.
      * try_spec - A TrySpec instance that specifies the builders to
        mirror and any try-specific settings.
      * python_api - Optional python API. If provided, in the event that
        a BuilderConfigException would be raised, an infra failing step
        will be created with the details instead.

    Raises:
      * BuilderConfigException if there isn't configuration matching all
        of builders in try_spec.mirrors and python_api is None.
      * InfraFailure if there isn't configuration matching all of
        builders in try_spec.mirrors and python_api is not None.
    """
    try:
      return cls(builder_db, try_spec)
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
  def lookup(cls, builder_id, builder_db, try_db=None, python_api=None):
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
      use the associated TrySpec, meaning it will wrap the BuilderSpecs
      for the mirrors in the TrySpec. Otherwise, the BuilderConfig will
      simply wrap the BuilderSpec associated with the builder.

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
    if try_db:
      try_spec = try_db.get(builder_id)

    # Some trybots do not mirror a CI bot. In this case, return a configuration
    # that uses the same <group, buildername> of the triggering trybot.
    if try_spec is None:
      try_spec = TrySpec.create([builder_id])

    return cls.create(builder_db, try_spec, python_api=python_api)

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

  # TODO(https://crbug.com/1193832) Remove this once all uses are changed to
  # builder_db
  @cached_property
  def bot_db(self):
    return self.builder_db

  @cached_property
  def builder_ids(self):
    return [m.builder_id for m in self.mirrors]

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
  def is_compile_only(self):
    return self._try_spec.execution_mode == COMPILE

  @cached_property
  def use_regression_test_selection(self):
    return self._try_spec.use_regression_test_selection

  @cached_property
  def regression_test_selection_recall(self):
    return self._try_spec.regression_test_selection_recall

  @cached_property
  def root_keys(self):
    keys = list(self.builder_ids)
    keys.extend(mirror.tester_id
                for mirror in self.mirrors
                if mirror.tester_id is not None)
    return keys

  @cached_property
  def all_keys(self):
    return self.builder_db.builder_graph.get_transitive_closure(self.root_keys)

  @cached_property
  def source_side_spec_files(self):
    groups = set(key.group for key in self.all_keys)
    return {g: '{}.json'.format(g) for g in groups}

  # TODO(https://crbug.com/1193832) Remove this once all callers are migrated to
  # use api.chromium_tests.create_target_config
  def create_build_config(self, chromium_tests_api, update_step):
    return chromium_tests_api.create_target_config(self, update_step)
