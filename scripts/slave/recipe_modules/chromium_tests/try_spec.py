# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import sys

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.attr_utils import (attrib, attrs, enum_attrib,
                                             mapping_attrib, sequence_attrib)

COMPILE_AND_TEST = 'compile/test'
COMPILE = 'compile'


@attrs()
class TryMirror(object):
  """An immutable specification for a trybot-mirroring relationship."""

  # The mirrored builder
  builder_id = attrib(chromium.BuilderId)
  # An optional builder that specifies tests that will be executed by the
  # associated trybot
  tester_id = attrib(chromium.BuilderId, default=None)

  def __attrs_post_init__(self):
    assert self.tester_id != self.builder_id, (
        "'tester_id' should not be equal to 'builder_id',"
        " pass None for 'tester_id'")

  @classmethod
  def create(cls, mastername, buildername, tester=None, tester_mastername=None):
    """Create a TryMirror.

    Args:
      mastername - The name of the mirrored builder's master.
      buildername - The name of the mirrored builder.
      tester - The name of the mirrored tester. If not provided, the
        returned TryMirror's tester_id field will be None.
      tester_mastername - The name of the mirrored tester's master. If
       not provided and tester is provided, then mastername will be
       used. Has no effect if tester is not provided.

    Returns:
      A TryMirror object. builder_id will be set to a BuilderId that
      identifies the mirrored builder. If tester is provided and the
      mirrored tester is not the same as the mirrored builder, tester_id
      will be set to a BuilderId that identifies the mirrored tester.
      Otherwise, tester_id will be set to None.
    """
    builder_id = chromium.BuilderId.create_for_master(mastername, buildername)
    tester_id = None
    if tester is not None:
      tester_id = chromium.BuilderId.create_for_master(
          tester_mastername or mastername, tester)
      if tester_id == builder_id:
        tester_id = None
    return cls(builder_id, tester_id)

  @classmethod
  def normalize(cls, mirror):
    """Converts various representations of a mirror to TryMirror.

    The incoming representation can have one of the following forms:
    * TryMirror - The input is returned.
    * BuilderId - A TryMirror with `builder_id` set to the input is
      returned.
    * A mapping containing the keys 'mastername' and 'buildername' and
      optionally 'tester' and 'tester_mastername' - The input is
      expanded as keyword arguments to TryMirror.create.
    """
    if isinstance(mirror, chromium.BuilderId):
      return cls(builder_id=mirror)
    if isinstance(mirror, TryMirror):
      return mirror
    return cls.create(**mirror)


@attrs()
class TrySpec(object):
  """Immutable specification for the operation of a try builder."""

  # The specifications of the builders being mirrored by the try builder
  mirrors = sequence_attrib(TryMirror)
  # The execution mode of the try builder.
  # * COMPILE_AND_TEST - Targets will be compiled and tests will be run.
  # * COMPILE - Targets will only be compiled, no tests will run
  execution_mode = enum_attrib([COMPILE_AND_TEST, COMPILE],
                               default=COMPILE_AND_TEST)
  # Additional names to add when analyzing the change to determine affected
  # targets
  analyze_names = sequence_attrib(str, default=())
  # Whether or not failed shards of tests should be retried
  retry_failed_shards = attrib(bool, default=True)

  @classmethod
  def create(cls, mirrors, **kwargs):
    """Create a TrySpec.

    Args:
      mirrors - A sequence of values that can be normalized to a TryMirror.
      kwargs - Values to apply to additional fields of the TrySpec.

    Returns:
      A TrySpec where:
      * The mirrors field is initialized with TryMirror instances normalized
        from mirrors.
      * The remaining fields are initialized with the values passed in kwargs.
    """
    mirrors = [TryMirror.normalize(m) for m in mirrors]
    return cls(mirrors=mirrors, **kwargs)

  @classmethod
  def create_for_single_mirror(cls,
                               mastername,
                               buildername,
                               tester=None,
                               tester_mastername=None,
                               **kwargs):
    """Create a TrySpec with a single mirror.

    Args:
      mastername - The name of the mirrored builder's master.
      buildername - The name of the mirrored builder.
      tester - The name of the mirrored tester. If not provided, the
        TrySpec's mirror's tester_id field will be None.
      tester_mastername - The name of the mirrored tester's master. If
       not provided and tester is provided, then mastername will be
       used. Has no effect if tester is not provided.
      kwargs - Values to apply to additional fields of the TrySpec.

    Returns:
      A TrySpec where:
      * The mirrors field has a single TryMirror instance create by
        calling TryMirror.create with mastername, buildername, tester
        and tester_mastername.
      * The remaining fields are initialized with the values passed in kwargs.
    """
    return cls.create(
        mirrors=[
            TryMirror.create(mastername, buildername, tester, tester_mastername)
        ],
        **kwargs)

  @classmethod
  def normalize(cls, spec):
    """Converts various representations of a try spec to TrySpec.

    The incoming representation can have one of the following forms:
    * TrySpec - The input is returned.
    * A mapping containing keys that match the field names of TrySpec -
      The input is expanded as keyword arguments to TrySpec.create.
    """
    if isinstance(spec, TrySpec):
      return spec
    return cls.create(**spec)


@attrs()
class TryDatabase(collections.Mapping):
  """A database that provides information for multiple try masters.

  TryDatabase provides access to the information contained in TryMasterSpec
  instances for multiple masters. Individual try builders can be looked up
  using mapping access with BuilderId as keys and TrySpec as values.
  """

  _db = mapping_attrib(chromium.BuilderId, TrySpec)

  @classmethod
  def create(cls, trybots_dict):
    """Create a TryDatabase from a dict.

    Args:
      trybots_dict - The mapping containing the information to create
        the database from. The keys of the mapping are the names of the
        try masters. The values of the mapping provide the information
        for the master and must be in a form that can be passed to
        TryMasterSpec.normalize.

    Returns:
    A new BotDatabase instance providing access to the information in
    trybots_dict.
    """
    db = {}

    for master_name, trybots_for_master in trybots_dict.iteritems():
      assert trybots_for_master.keys() != [
          'builders'
      ], "Remove unnecessary 'builders' level"

      for builder_name, try_spec in trybots_for_master.iteritems():
        builder_id = chromium.BuilderId.create_for_master(
            master_name, builder_name)
        try:
          try_spec = TrySpec.normalize(try_spec)
        except Exception as e:
          # Re-raise the exception with information that identifies the master
          # that is problematic
          message = '{} while creating try spec for builder {!r}'.format(
              e.message, builder_id)
          raise type(e)(message), None, sys.exc_info()[2]

        db[builder_id] = try_spec

    return cls(db)

  @classmethod
  def normalize(cls, try_db):
    """Converts representations of try database to TryDatabase.

    The incoming representation can have one of the following forms:
    * TryDatabase - The input is returned.
    * A mapping containing keys with try master names and values
      representing try master specs that can be normalized via
      TryMasterSpec.normalize - The input is passed to
      TryDatabase.create.
    """
    if isinstance(try_db, TryDatabase):
      return try_db
    return cls.create(try_db)

  def __getitem__(self, key):
    return self._db[key]

  def __iter__(self):
    return iter(self._db)

  def __len__(self):
    return len(self._db)
