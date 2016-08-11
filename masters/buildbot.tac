# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common twistd configuration for buildbot.

Use this with:
  twistd -y buildbot.tac -d path/to/master
"""

import os

from twisted.application import service
from buildbot.master import BuildMaster

application = service.Application('buildmaster')
BuildMaster(os.getcwd(), 'master.cfg').setServiceParent(application)
