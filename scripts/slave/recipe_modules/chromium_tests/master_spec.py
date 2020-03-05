# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys

from . import bot_spec as bot_spec_module

from RECIPE_MODULES.build.attr_utils import (FieldMapping, attrib, attrs,
                                             mapping_attrib, sequence_attrib)


@attrs()
class MasterSettings(object):
  """An immutable object containing the per-master settings."""

  luci_project = attrib(str, default='chromium')
  build_gs_bucket = attrib(str, default=None)

  bisect_builders = sequence_attrib(str, default=())
  bisect_build_gs_bucket = attrib(str, default=None)
  bisect_build_gs_extra = attrib(str, default=None)

  @classmethod
  def create(cls, **kwargs):
    """Create a MasterSettings.

    Arguments:
      kwargs - Values to initialize the MasterSettings.

    Returns:
      A new MasterSettings instance with fields set to the values in
      kwargs and all other fields set to their defaults.
    """
    return cls(**kwargs)

  @classmethod
  def normalize(cls, settings):
    """Converts representations of master settings to MasterSettings.

    The incoming representation can have one of the following forms:
    * MasterSettings - The input is returned.
    * A mapping containing keys matching the fields to initialize - The
      input is expanded as keyword arguments to MasterSettings.create.
    """
    if isinstance(settings, MasterSettings):
      return settings
    return cls.create(**settings)


@attrs()
class MasterSpec(object):
  """An immutable specification for a master.

  Th spec includes the settings for the master as well as the specs for its
  associated builders.
  """

  settings = attrib(MasterSettings, default=MasterSettings.create())
  builders = mapping_attrib(str, bot_spec_module.BotSpec, default={})

  @classmethod
  def create(cls, settings=None, builders=None):
    """Create a MasterSpec.

    Arguments:
      settings - The optional settings for the master. If provided, must
        be in a form that can be passed to MasterSettings.normalize.
      builders - The builders associated with the master. It must be a
        mapping that maps builder names to their spec. The specs for
        each builder must be in a form that can be passed to BotSpec.normalize.

    Returns:
      A new MasterSpec instance with settings set to the normalized
      MasterSettings instances and builders set to a mapping with
      normalized BotSpec instances for values.
    """
    kwargs = {}
    if settings is not None:
      kwargs['settings'] = MasterSettings.normalize(settings)
    if builders is not None:

      def get_bot_spec(name, spec):
        try:
          return bot_spec_module.BotSpec.normalize(spec)
        except Exception as e:
          # Re-raise the exception with information that identifies the builder
          # dict that is problematic
          message = '{} while creating spec for builder {!r}: {}'.format(
              e.message, name, spec)
          raise type(e)(message), None, sys.exc_info()[2]

      kwargs['builders'] = {
          name: get_bot_spec(name, spec) for name, spec in builders.iteritems()
      }
    return cls(**kwargs)

  @classmethod
  def normalize(cls, spec):
    """Converts representations of a master spec to MasterSpec.

    The incoming representation can have one of the following forms:
    * MasterSpec - The input is returned.
    * A mapping containing some subset of the keys 'builder' and
      'settings' - The input is expanded as keyword arguments to
      MasterSpec.create.
    """
    if isinstance(spec, MasterSpec):
      return spec
    return cls.create(**spec)
