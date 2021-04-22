# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

from . import builder_spec as builder_spec_module

from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             mapping)
from RECIPE_MODULES.build.chromium import BuilderId


def _migration_validation(builder_id, builder_spec):
  """Validate that back-sliding of BuilderSpec migrations does not occur."""
  if builder_spec.test_specs:
    assert builder_id.group in (
        'chrome.pgo',
        'chromium.webrtc',

        # Used for testing the migration
        'fake-group',
    ), ('Builder: {!r}\nUse of the test_specs field is deprecated,'
        ' instead update the source side spec file for builder group {!r}.'
        ' Contact gbeaty@ if you need assistance.').format(
            builder_id, builder_id.group)

  elif builder_spec.swarming_dimensions:
    assert builder_id.group in (
        'chromium.clang',
        'chromium.fyi',
        'chromium.webrtc',

        # Used for tests of the code that consumes swarming_dimensions
        'chromium.findit',
        'test_group',
    ), ('Builder: {!r}\nUse of the swarming_dimensions field is deprecated,'
        ' instead update the source side spec file for builder group {!r}.'
        ' Contact gbeaty@ if you need assistance., {}').format(
            builder_id, builder_id.group, builder_spec.swarming_dimensions)


@attrs()
class BuilderDatabase(collections.Mapping):
  """A database that provides information for multiple groups.

  BuilderDatabase provides access to the information contained in GroupSpec
  instances for multiple groups. Individual builders can be looked up
  using mapping access with BuilderId as keys and BuilderSpec as values.
  Information for an entire group can be accessed through the
  group_specs field, which maps group to GroupSpec.
  """

  _db = attrib(mapping[BuilderId, builder_spec_module.BuilderSpec])
  builders_by_group = attrib(
      mapping[str, mapping[str, builder_spec_module.BuilderSpec]])

  @classmethod
  def create(cls, builder_dict):
    """Create a BuilderDatabase from a dict.

    Args:
      * builder_dict - The mapping containing the information to create
        the database from. The keys of the mapping are the names of the
        groups. The values of the mapping are themselves mappings with
        the keys being builder names and the values BuilderSpec
        instances for the associated builder.

    Returns: A new BuilderDatabase instance providing access to the
    information in builder_dict.
    """
    db = {}
    builders_by_group = {}

    for group, builders_for_group in builder_dict.iteritems():
      builders_for_group = dict(builders_for_group)
      for builder_name, builder_spec in builders_for_group.iteritems():
        assert isinstance(builder_spec,
                          builder_spec_module.BuilderSpec), builder_spec
        builder_id = BuilderId.create_for_group(group, builder_name)
        _migration_validation(builder_id, builder_spec)

        builders_for_group[builder_name] = builder_spec
        db[builder_id] = builder_spec

      builders_by_group[group] = builders_for_group

    return cls(db, builders_by_group)

  # TODO(https://crbug.com/1193832) Remove this once all callers are migrated to
  # use builder_graph
  @cached_property
  def bot_graph(self):
    return self.builder_graph  # pragma: no cover

  @cached_property
  def builder_graph(self):
    """The graph of all of the builders stored in the database."""
    return BuilderGraph.create(self)

  def __getitem__(self, key):
    return self._db[key]

  def __iter__(self):
    return iter(self._db)

  def __len__(self):
    return len(self._db)


@attrs()
class BuilderGraph(collections.Mapping):
  """A graph of the parent-child relationship between builders.

  BuilderGraph provides a mapping interface where a BuilderId key can be
  used to retrieve a set of BuilderId instances that identify the
  children of the builder identified by the key. It also provides a
  transitive closure operation for retrieving the transitive descendants
  of a set of keys.
  """

  _graph = attrib(mapping[BuilderId, frozenset])

  @classmethod
  def create(cls, db):
    graph = {key: set() for key in db}

    for builder_id, builder_spec in db.iteritems():
      if builder_spec.parent_buildername is None:
        continue

      parent_id = BuilderId.create_for_group(
          builder_spec.parent_builder_group or builder_id.group,
          builder_spec.parent_buildername)
      graph[parent_id].add(builder_id)

    return cls(graph)

  def get_transitive_closure(self, roots):
    """Get the set of IDs that are descendants of the provided roots."""
    closure = set()
    to_examine = list(roots)
    while to_examine:
      key = to_examine.pop()
      if key in closure:
        continue
      to_examine.extend(self[key])
      closure.add(key)
    return closure

  def __getitem__(self, key):
    return self._graph[key]

  def __iter__(self):
    return iter(self._graph)

  def __len__(self):
    return len(self._graph)
