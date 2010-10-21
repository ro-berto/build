# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re

from buildbot import buildset
from buildbot.changes.changes import Change
from buildbot.process.properties import Properties
from buildbot.scheduler import BadJobfile
from buildbot.scheduler import TryBase
from twisted.python import log
from twisted.web import http

from master.try_job_stamp import TryJobStamp


class TryJobBase(TryBase):
  """Implement ParseJob."""

  # Simplistic email matching regexp.
  _EMAIL_VALIDATOR = re.compile(
      r'[a-zA-Z\.\+\-\_]+@[a-zA-Z\.\-]+\.[a-zA-Z]{2,3}$')

  def __init__(self, name, pools, properties,
               last_good_urls, code_review_sites):
    # TryBase.__init__ expects {}
    TryBase.__init__(self, name, pools.ListBuilderNames(), properties or {})
    self.pools = pools
    pools.SetParent(self)
    self.last_good_urls = last_good_urls
    self.code_review_sites = code_review_sites

  def ParseJob(self, options):
    """Grab try job settings."""
    job_name = options.get('name', 'Unnamed')
    user = options.get('user', 'John Doe')
    emails = options.get('email', '').split(',')
    # Email sanitization.
    for email in emails:
      if not TryJobBase._EMAIL_VALIDATOR.match(email):
        log.msg("'%s' is an invalid email address!" % email)
        raise BadJobfile("'%s' is an invalid email address!" % email)

    diff = options.get('patch', None)
    root = options.get('root', None)
    clobber = options.get('clobber')
    # -pN argument to patch.
    patchlevel = int(options.get('patchlevel', 0))
    branch = options.get('branch', None)
    revision = options.get('revision', None)
    buildset_id = options.get('reason', '%s: %s' % (user, job_name))
    testfilters = [item for item in options.get('testfilter', '').split(',')
                   if item]
    project = options.get('project', self.pools.default_pool_name)

    # Code review infos. Enforce numbers.
    patchset = options.get('patchset', None)
    if patchset:
      patchset = int(patchset)
    issue = options.get('issue', None)
    if issue:
      issue = int(issue)

    builder_names = []
    if 'bot' in options:
      builder_names = options['bot'].split(',')
    # TODO(maruel): Don't select the builders right now if not specified.
    builder_names = self.pools.Select(builder_names, project)
    log.msg('Choose %s for job %s' % (','.join(builder_names), buildset_id))
    if diff:
      patch = (patchlevel, diff, root)
    else:
      patch = None

    # There can be only one to blame per change.
    fake_changes = [Change(email, [''], '',
                           revision=revision) for email in emails]
    last_good_url = None
    if self.last_good_urls:
      last_good_url = self.last_good_urls.get(project)
    code_review_site = None
    if self.code_review_sites:
      code_review_site = self.code_review_sites.get(project)
    jobstamp = TryJobStamp(branch=branch, revision=revision, patch=patch,
                           changes=fake_changes,
                           last_good_url=last_good_url,
                           code_review_site=code_review_site,
                           job_name=job_name, patchset=patchset, issue=issue)
    # Current job extra properties that are not related to the source stamp.
    # Initialize with the Scheduler's base properties.
    props = Properties()
    props.updateFromProperties(self.properties)
    if clobber:
      props.setProperty('clobber', True, 'Scheduler')
    if testfilters:
      props.setProperty('testfilters', testfilters, 'Scheduler')
    return builder_names, jobstamp, buildset_id, props

  def CancelJobsMatching(self, build_set, builder_names):
    """Cancels any jobs with the same job and owner."""

    if (not isinstance(build_set.source, TryJobStamp) or
        len(build_set.source.changes) != 1):
      # Not a try job.
      return

    for builder_name in builder_names:
      # pylint: disable=E1101
      # TODO(maruel): remove once pylint improves its type inference.
      builder = self.parent.botmaster.builders[builder_name]
      # Cancel any jobs that haven't yet started.
      for buildable in builder.buildable:
        if build_set.source.canReplace(buildable.source):
          builder.cancelBuildRequest(buildable)
          log.msg('Canceling job %s on %s' % (build_set.source.job_name,
                                              builder.name))
          break # There should only be one try with a given name.

      # Mark any running builds as canceled. In theory we could cancel these too
      # in practice cancelling might leave the bot in a weird state. Instead we
      # set canceled to true so that after the current step finishes the builder
      # doesn't execute any more steps.
      for build in builder.building:
        for request in build.requests:
          if build_set.source.canReplace(request.source):
            # The request copies the stamp. Set the stamp for both so
            # that the canceled state is reflected in both places.
            build.source.canceled = True
            request.source.canceled = True
            log.msg('Marking %s as canceled on %s' %
                    (build_set.source.job_name, builder_name))

  def SubmitJob(self, options):
    """Queues the buildset.

    Args:
      options: an optparse set of options.

    Returns: an HTTP error code.

    The content of options is decoded by ParseJob. If the file 'disable_try'
    exists in the current directory, the try server is disabled.
    """
    if os.path.exists('disable_try'):
      log.msg('Try job cancelled because the server is disabled!')
      return http.SERVICE_UNAVAILABLE

    try:
      builder_names, jobstamp, buildset_id, props = self.ParseJob(options)
    except BadJobfile:
      log.msg('%s reports a bad job connection' % (self))
      log.err()
      return http.BAD_REQUEST
    reason = "'%s' try job" % buildset_id
    bs = buildset.BuildSet(builder_names, jobstamp, reason=reason,
                           bsid=buildset_id, properties=props)
    # pylint: disable=E1101
    self.CancelJobsMatching(bs, builder_names)
    self.parent.submitBuildSet(bs)
    return http.OK
