# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.pb import ChangePerspective, PBChangeSource
from twisted.internet import defer


class ChangePerspectiveWithComparator(ChangePerspective):
  def __init__(self, comparator, *args, **kwargs):
    self.comparator = comparator
    ChangePerspective.__init__(self, *args, **kwargs)

  def perspective_addChange(self, changedict):
    self.comparator.addRevision(changedict.get('revision'))
    return ChangePerspective.perspective_addChange(self, changedict)


class PBChangeSourceWithComparator(PBChangeSource):
  def __init__(self, comparator, *args, **kwargs):
    self.comparator = comparator
    PBChangeSource.__init__(self, *args, **kwargs)

  def getPerspective(self, _mind, username):
    assert username == self.user
    return ChangePerspectiveWithComparator(
        self.comparator, self.master, self.prefix)
