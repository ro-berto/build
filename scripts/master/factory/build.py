#!/usr/bin/python
# Copyright (c) 2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Inherits buildbot.process.base.Build to add BuildFactory inherited
properties and support for TryJob.canceled."""

from buildbot.process import base
from buildbot.status.builder import SKIPPED
from twisted.python import log

class Build(base.Build):
  """Build class that inherits the BuildFactory properties."""

  def __init__(self, request, factory_properties):
    base.Build.__init__(self, request)
    self._factory_properties = factory_properties

  def setupProperties(self):
    """Adds BuildFactory inherited properties."""
    base.Build.setupProperties(self)
    self.getProperties().updateFromProperties(self._factory_properties)

  def stepDone(self, result, step):
    """Overriden to skip remaining steps if the job is canceled."""
    terminate = base.Build.stepDone(self, result, step)
    if terminate:
      return True
    for request in self.requests:
      if getattr(request.source, 'canceled', False):
        self.result = SKIPPED
        return True
    return False
