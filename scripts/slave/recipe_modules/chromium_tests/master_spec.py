# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys

from . import bot_spec as bot_spec_module

from RECIPE_MODULES.build.attr_utils import attrs, mapping_attrib


@attrs()
class MasterSpec(object):
  """An immutable specification for a master.

  Th spec includes the settings for the master as well as the specs for its
  associated builders.
  """

  builders = mapping_attrib(str, bot_spec_module.BotSpec, default={})

  @classmethod
  def create(cls, builders=None):
    """Create a MasterSpec.

    Arguments:
      builders - The builders associated with the master. It must be a
        mapping that maps builder names to their spec. The specs for
        each builder must be in a form that can be passed to BotSpec.normalize.

    Returns:
      A new MasterSpec instance with settings set to the normalized
      MasterSettings instances and builders set to a mapping with
      normalized BotSpec instances for values.
    """
    kwargs = {}
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
