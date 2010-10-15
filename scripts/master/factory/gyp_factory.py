#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""BuildFactory creator to run GYP tests."""

import os

from buildbot.steps.shell import ShellCommand

import config
from master.factory import gclient_factory


class GYPFactory(gclient_factory.GClientFactory):
  svn_url = config.Master.gyp_trunk_url

  def __init__(self, build_dir, **kw):
    main = gclient_factory.GClientSolution(self.svn_url)
    super(GYPFactory, self).__init__(build_dir, [main], **kw)

  def GYPFactory(self, formats):
    f = self.BaseFactory()
    for format_val in formats:
      cmd = [
          'python',
          os.path.join(self._build_dir, 'gyptest.py'),
          '--all',
          '--passed',
          '--format', format_val,
          '--chdir', self._build_dir,
          '--path', '../scons'
      ]
      f.addStep(ShellCommand, description=format, command=cmd)
    return f
