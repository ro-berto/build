# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import build_utils

from buildbot.changes.pb import PBChangeSource
from buildbot.changes import svnpoller

def Update(config, active_master, c):
  # Polls config.Master.trunk_url for changes
  c['change_source'].append(PBChangeSource())