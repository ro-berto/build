# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.attr_utils import (FieldMapping, attrib, attrs,
                                             mapping_attrib, sequence_attrib)


@attrs()
class BuilderId(object):
  """ID type identifying a builder.

  Currently, the ID identifies a builder by the pair of mastername and
  buildername. This type provides a means for modifying the underlying
  ID data without having to modify code that simply needs to provide an
  ID to some other code (e.g. switching to project, bucket, builder).
  """

  master = attrib(str)
  builder = attrib(str)

  @classmethod
  def create_for_master(cls, mastername, builder):
    return cls(mastername, builder)


@attrs()
class BuilderSpec(FieldMapping):
  """An immutable specification for a builder.

  This type provides the means of specifying all of the input values for a
  builder. Previously, dictionaries were used which have the following
  drawbacks:
    * Susceptible to typos for key names
    * Lack of validation at definition time
    * Poor discoverability of available fields
    * Default values for fields are specified at the point(s) of access

  This type address the first 2 points. The 3rd point is also addressed with the
  caveat that recipes/recipe modules that add their own information to the spec
  require a type containing fields with the additional information. To remain
  backwards compatible with existing code, the 4th point is not addressed yet.

  Backwards compatibility:
  Until callers have switched over to accessing the fields directly, a
  BuilderSpec acts as a mapping with an item for each field whose value is not
  None, with the name of the field as the key.
  """

  # The name of the config to use for the chromium recipe module
  chromium_config = attrib(str, default=None)
  # The names of additional configs to apply for the chromium recipe module
  chromium_apply_config = sequence_attrib(str, default=())
  # The keyword arguments used when setting the config for the chromium recipe
  # module
  chromium_config_kwargs = mapping_attrib(str, default={})
  # The names of additional configs to apply for the gclient recipe module
  gclient_apply_config = sequence_attrib(str, default=())

  # A bool controlling whether have bot_update perform a clobber of any
  # pre-existing build outputs
  clobber = attrib(bool, default=False)
  # A path relative to the checkout to the root where the patch should be
  # applied in bot_update
  patch_root = attrib(str, default=None)

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)
