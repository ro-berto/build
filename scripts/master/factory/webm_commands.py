# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds webm-specific commands."""

from master.factory import commands

class WebMCommands(commands.FactoryCommands):
  """Encapsulates methods to add chromium commands to a buildbot factory."""

  def __init__(self, factory=None, identifier=None, target=None,
               build_dir=None, target_platform=None):

    commands.FactoryCommands.__init__(self, factory, identifier,
                                      target, build_dir, target_platform)
