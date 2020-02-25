# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.attr_utils import attrib, attrs


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
