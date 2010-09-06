# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module for chromium-os-specific git source that dumps revisions."""

import copy

from buildbot.steps import source
from buildbot.process import buildstep

# Relative path to revision file for cbuildbot.
PFQ_REVISION_FILE = 'crosutils/bin/revisions.pfq'

class GitRevisionDropper(source.Source):
  """Drops a list of revisions from multiple git repositories."""

  name = 'gitrevisiondropper'

  def computeSourceRevision(self, changes):
    """Creates a list of revision numbers.  Revision numbers coming from 
    cros git hooks are folder_name:revision.

    This is a hook method provided by the parent source.Source class and
    default implementation in source.Source returns None. Return value of this
    method is be used to set 'revision' argument value for startVC() method."""
    revision_list = ''
    if not changes:
      return None

    def GrabRevision(change):
      """Handle revision == None or any invalid value."""
      return '%s@%s' % (change.repository, change.revision)

    for change in changes:
      revision = GrabRevision(change)
      revision_list = '%s %s' % (revision_list, revision)
    revision_list = revision_list.strip()
    return revision_list

  def startVC(self, branch, revision, patch):
    """Drops a source stamp for other steps"""
    args = copy.copy(self.args)
    args['command'] = 'echo "%s" > %s' % (revision, PFQ_REVISION_FILE)
    # Shell is defined by buildbot.slave.SlaveShellCommand.
    cmd = buildstep.LoggedRemoteCommand("shell", args)
    self.startCommand(cmd, [])
