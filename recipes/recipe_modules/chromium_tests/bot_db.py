# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import collections
import sys

from . import bot_spec as bot_spec_module

from recipe_engine.types import FrozenDict

from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             mapping_attrib, sequence_attrib)
from RECIPE_MODULES.build.chromium.types import BuilderId


def _migration_validation(builder_id, builder_spec):
  """Validate that back-sliding of BotSpec migrations does not occur."""
  if builder_spec.test_specs:
    assert builder_id.group in (
        'chrome.pgo',
        'chromium.clang',
        'chromium.perf',
        'chromium.perf.fyi',
        'chromium.webrtc',
        'official.chromeos.continuous',

        # Used for testing the migration
        'fake-group',
    ), ('Builder: {!r}\nUse of the test_specs field is deprecated,'
        ' instead update the source side spec file for builder group {!r}.'
        ' Contact gbeaty@ if you need assistance.').format(
            builder_id, builder_id.group)

  elif builder_spec.swarming_dimensions:
    assert builder_id.group in (
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
class BotDatabase(collections.Mapping):
  """A database that provides information for multiple groups.

  BotDatabase provides access to the information contained in GroupSpec
  instances for multiple groups. Individual builders can be looked up
  using mapping access with BuilderId as keys and BotSpec as values.
  Information for an entire group can be accessed through the
  group_specs field, which maps group to GroupSpec.
  """

  _db = mapping_attrib(BuilderId, bot_spec_module.BotSpec)
  builders_by_group = mapping_attrib(str, FrozenDict)

  @classmethod
  def create(cls, bots_dict):
    """Create a BotDatabase from a dict.

    Args:
      bots_dict - The mapping containing the information to create the
        database from. The keys of the mapping are the names of the
        groups. The values of the mapping provide the information for
        the group and must be in a form that can be passed to
        GroupSpec.normalize.

    Returns:
    A new BotDatabase instance providing access to the information in
    bots_dict.
    """
    db = {}
    builders_by_group = {}

    for group, builders_for_group in bots_dict.iteritems():
      assert builders_for_group.keys() != [
          'builders'
      ], "Remove unnecessary 'builders' level"

      builders_for_group = dict(builders_for_group)
      for builder_name, builder_spec in builders_for_group.iteritems():
        builder_id = BuilderId.create_for_group(group, builder_name)
        try:
          builder_spec = bot_spec_module.BotSpec.normalize(builder_spec)
        except Exception as e:
          # Re-raise the exception with information that identifies the group
          # that is problematic
          message = '{} while creating spec for builder {!r}'.format(
              e.message, builder_id)
          raise type(e)(message), None, sys.exc_info()[2]

        _migration_validation(builder_id, builder_spec)

        builders_for_group[builder_name] = builder_spec
        db[builder_id] = builder_spec

      builders_by_group[group] = builders_for_group

    return cls(db, builders_by_group)

  @classmethod
  def normalize(cls, bot_db):
    """Converts representations of bot database to BotDatabase.

    The incoming representation can have one of the following forms:
    * BotDatabase - The input is returned.
    * A mapping containing keys with groups and values representing
      group specs that can be normalized via GroupSpec.normalize - The
      input is passed to BotDatabase.create.
    """
    if isinstance(bot_db, BotDatabase):
      return bot_db
    return cls.create(bot_db)

  @cached_property
  def bot_graph(self):
    """The graph of all of the bots stored in the database."""
    return BotGraph.create(self)

  def __getitem__(self, key):
    return self._db[key]

  def __iter__(self):
    return iter(self._db)

  def __len__(self):
    return len(self._db)


@attrs()
class BotGraph(collections.Mapping):
  """A graph of the parent-child relationship between builders.

  BotGraph provides a mapping interface where a BuilderId key can be
  used to retrieve a set of BuilderId instances that identify the
  children of the builder identified by the key. It also provides a
  transitive closure operation for retrieving the transitive descendants
  of a set of keys.
  """

  _graph = mapping_attrib(BuilderId, frozenset)

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
