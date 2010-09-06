#!/usr/bin/python
# Copyright (c) 2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility classes to enhance process.properties.Properties usefulness."""


from buildbot.process.properties import WithProperties


class ListProperties(WithProperties):
  """Act like a list but skip over items that are None.

  This class doesn't use WithProperties methods but inherits from it since it is
  used as a flag in Properties.render() to defer the actual work to
  self.render()."""

  compare_attrs = ('items')

  def __init__(self, items):
    """items should be a list."""
    # Dummy initialization.
    WithProperties.__init__(self, '')
    self.items = items

  def render(self, pmap):
    results = []
    # For each optional item, look up the corresponding property in the
    # PropertyMap.
    for item in self.items:
      if isinstance(item, WithProperties):
        item = item.render(pmap)
      # Skip over None items.
      if item is not None and item != '':
        results.append(item)
    return results
