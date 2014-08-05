# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes import svnpoller

from common import chromium_utils

from master import build_utils

import config

def ChromeTreeFileSplitter(path):
  """split_file for the 'src' project in the trunk."""

  # Exclude .DEPS.git from triggering builds on chrome.
  if path == 'src/.DEPS.git':
    return None

  # List of projects we are interested in. The project names must exactly
  # match paths in the Subversion repository, relative to the 'path' URL
  # argument. build_utils.SplitPath() will use them as branch names to
  # kick off the Schedulers for different projects.
  projects = ['src']
  return build_utils.SplitPath(projects, path)


class ChromiumSvnPoller(svnpoller.SVNPoller):
  def __init__(self, svnurl=None, svnbin=None, split_file=None,
               pollinterval=None, revlinktmpl=None,
               *args, **kwargs):
    if svnurl is None:
      svnurl = config.Master.trunk_url

    if svnbin is None:
      svnbin = chromium_utils.SVN_BIN

    if split_file is None:
      split_file = ChromeTreeFileSplitter

    if revlinktmpl is None:
      revlinktmpl = (
          'http://src.chromium.org/viewvc/chrome?view=rev&revision=%s')

    if pollinterval is None:
      pollinterval = 10

    svnpoller.SVNPoller.__init__(
        self, svnurl=svnurl, svnbin=svnbin, split_file=split_file,
        pollinterval=pollinterval, revlinktmpl=revlinktmpl, *args, **kwargs)
