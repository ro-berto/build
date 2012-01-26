# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes import svnpoller

class SVNPoller(svnpoller.SVNPoller):
  """Adds necessary information to add (CQ) tag to waterfall/console views."""

  def get_logs(self, _):
    """Uses an additional --with-all-revprops argument for svn log so that it
       has necessary information to know whether a commit was made by the
       commit-queue."""
    args = []
    args.extend(["log", "--xml", "--verbose", "--non-interactive",
        "--with-all-revprops"])
    if self.svnuser:
      args.extend(["--username=%s" % self.svnuser])
    if self.svnpasswd:
      args.extend(["--password=%s" % self.svnpasswd])
    args.extend(["--limit=%d" % (self.histmax), self.svnurl])
    d = self.getProcessOutput(args)
    return d

  def create_changes(self, new_logentries):
    """Adds a key 'cq' in each change dict. The value is set to ' (CQ)' if the
       change was committed by the commit-queue."""
    def commit_bot_used(logentry):
      revprops = logentry.getElementsByTagName('revprops')
      if revprops is not None:
        for revprop in revprops.getElementsByTagName('property'):
          if revprop.getAttribute("name") == "commit-bot":
            return True
      return False

    revcq = {}
    for el in new_logentries:
      if commit_bot_used(el):
        revcq[str(el.getAttribute("revision"))] = True

    changes = svnpoller.SVNPoller.create_changes(self, new_logentries)
    for change in changes:
      if change.revision in revcq:
        change['cq'] = " (CQ)"
      else:
        change['cq'] = ""

    return changes
