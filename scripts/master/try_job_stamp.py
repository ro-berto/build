# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Define a job to try."""

import copy
import datetime
import urllib2

from buildbot.sourcestamp import SourceStamp
from twisted.python import log


class TryJobStamp(SourceStamp):
  """Store additional information about a source specific run to execute. Just
  storing the actual patch (like SourceStamp does) is insufficient."""
  _last_known_good_rev = 0

  compare_attrs = ('branch', 'revision', 'patch', 'changes',
      'job_name_stripped', 'issue')

  def __init__(self, job_name=None, timestamp=None, patchset=None, issue=None,
      last_good_url=None, code_review_site=None, canceled=None, **kwargs):
    SourceStamp.__init__(self, **kwargs)
    self.job_name = job_name
    self.job_name_stripped = job_name.split('#', 1)[0]
    self.timestamp = timestamp
    self.patchset = patchset
    self.issue = issue
    self.last_good_url = last_good_url
    self.code_review_site = code_review_site
    self.canceled = canceled

    # TODO(maruel): This should be chosen at Build start, not a queuing
    # time.
    if not self.revision and self.last_good_url:
      # Grab last known good revision number.
      try:
        connection = urllib2.urlopen(self.last_good_url)
        self.revision = int(connection.read().strip())
        connection.close()
        TryJobStamp._last_known_good_rev = self.revision
      except (ValueError, IOError):
        if TryJobStamp._last_known_good_rev:
          self.revision = TryJobStamp._last_known_good_rev
    else:
      # By definition when self.revision is None, HEAD will be used at update
      # time. Also use HEAD when there is no lkgr server for this project.
      # TODO(maruel): Always grab the current HEAD revision right here. The
      # reason is simple; if the user commits right after his try, the slaves
      # will grab the revision containing the patch so the patch won't apply.
      # Note that this code path is only used when lkgr is down.
      pass

    # Print out debug info.
    patch_info = '(No patch)'
    if self.patch:
      patch_info = "-p%d (%d bytes) (base: %s)" % (self.patch[0],
                                                   len(self.patch[1]),
                                                   self.patch[2])
    self.timestamp = datetime.datetime.utcnow()
    revision_info = 'no rev'
    if self.revision:
      revision_info = 'rev %s' % str(self.revision)
    log.msg("Created TryJobStamp %s, %s, %s" % (
        str(self.job_name),
        revision_info,
        patch_info))

    # Keeps job results.
    self.results = {}

  def canBeMergedWith(self, other):
    """Try jobs shouldn't be merged together!"""
    # TODO(maruel):  if self.patch == other.patch: return True ?
    return False

  def canReplace(self, other):
    """Returns true if this job can replace other.

    It checks that the same person initiated both tries and that the job names
    match. Anything after # in a job name is ignored."""

    return (len(self.changes) == 1 and
            isinstance(other, TryJobStamp) and
            len(other.changes) == 1 and
            self.job_name.split('#', 1)[0] ==
                other.job_name.split('#', 1)[0] and
            self.changes[0].who == other.changes[0].who)

  def mergeWith(self, others):
    new_changes = SourceStamp.mergeWith(self, others)
    new_stamp = copy.copy(self)
    new_stamp.changes = new_changes.changes
    return new_stamp

  def getAbsoluteSourceStamp(self, got_revision):
    new_stamp = copy.copy(self)
    new_stamp.revision = got_revision
    new_stamp.changes = []
    return new_stamp

  def getCodeReviewStatusUrl(self):
    if self.issue and self.patchset and self.code_review_site:
      return self.code_review_site % (self.issue, self.patchset)

  def asDict(self):
    result = SourceStamp.asDict(self)
    result['timestamp'] = self.timestamp.isoformat()
    result['issue'] = self.issue
    result['patchset'] = self.patchset
    result['job_name'] = self.job_name
    result['canceled'] = self.canceled
    return result
