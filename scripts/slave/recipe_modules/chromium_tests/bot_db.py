# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import collections
import sys

from . import bot_spec as bot_spec_module, master_spec as master_spec_module

from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             mapping_attrib, sequence_attrib)
from RECIPE_MODULES.build.chromium.types import BuilderId


@attrs()
class BotDatabase(collections.Mapping):
  """A database that provides information for multiple masters.

  BotDatabase provides access to the information contained in MasterSpec
  instances for multiple masters. Individual builders can be looked up
  using mapping access with BuilderId as keys and BotSpec as values.
  Information for an entire master can be accessed through the
  master_specs field, which maps mastername to MasterSpec.
  """

  _db = mapping_attrib(BuilderId, bot_spec_module.BotSpec)
  master_specs = mapping_attrib(str, master_spec_module.MasterSpec)

  @classmethod
  def create(cls, bots_dict):
    """Create a BotDatabase from a dict.

    Args:
      bots_dict - The mapping containing the information to create the
        database from. The keys of the mapping are the names of the
        masters. The values of the mapping provide the information for
        the master and must be in a form that can be passed to
        MasterSpec.normalize.

    Returns:
    A new BotDatabase instance providing access to the information in
    bots_dict.
    """
    db = {}
    master_specs = {}

    for master_name, master_spec in bots_dict.iteritems():
      try:
        master_spec = master_spec_module.MasterSpec.normalize(master_spec)
      except Exception as e:
        # Re-raise the exception with information that identifies the master
        # that is problematic
        message = '{} while creating spec for master {!r}'.format(
            e.message, master_name)
        raise type(e)(message), None, sys.exc_info()[2]

      master_specs[master_name] = master_spec

      for builder_name, builder_spec in master_spec.builders.iteritems():
        builder_id = BuilderId.create_for_master(master_name, builder_name)
        db[builder_id] = builder_spec

    return cls(db, master_specs)

  @classmethod
  def normalize(cls, bot_db):
    """Converts representations of bot database to BotDatabase.

    The incoming representation can have one of the following forms:
    * BotDatabase - The input is returned.
    * A mapping containing keys with master names and values
      representing master specs that can be normalized via
      MasterSpec.normalize - The input is passed to BotDatabase.create.
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

      parent_id = BuilderId.create_for_master(
          builder_spec.parent_mastername or builder_id.master,
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
