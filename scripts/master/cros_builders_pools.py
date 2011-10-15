# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Implement builder selection for CrOS."""

from master.builders_pools import BuildersPools

class CrOSBuildersPools(BuildersPools):
  """Adds support for builder config->name mappings."""

  def __init__(self, default_pool_name, builder_mapping, parent=None):
    BuildersPools.__init__(self, default_pool_name, parent)
    self._builder_mapping = builder_mapping

  def Select(self, builder_names=None, pool_name=None):
    """Returns list of selected builder names.

    Args:
      builder_names: A list of CrOS build configurations (i.e.,
                     x86-generic-pre-flight-queue) to select.
      pool_name: The builder pool to look in.

    Returns:
      A list of buildbot builder names.
    """
    # If the user has requested specific build configurations, return the
    # corresponding builder names.
    if builder_names:
      return [self._builder_mapping.get(name) for name in builder_names]
    else:
      return BuildersPools.Select(self, None, pool_name)
