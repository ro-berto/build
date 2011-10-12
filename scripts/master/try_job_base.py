# Copyright (c) 2011 The Chromium Authors. All rights reserved.
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
      r'[a-zA-Z][a-zA-Z0-9\.\+\-\_]*@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,3}$')

  def __init__(self, name, pools, properties,
               last_good_urls, code_review_sites):
    # TryBase.__init__ expects {}
    TryBase.__init__(self, name, pools.ListBuilderNames(), properties or {})
    self.pools = pools
    pools.SetParent(self)
    self.last_good_urls = last_good_urls
    self.code_review_sites = code_review_sites

  def parse_options(self, options):
    """Converts try job settings into a dict."""
    # Flush None and '' keys.
    options = dict(
        (k, v) for k, v in options.iteritems() if v not in (None, ''))

    options.setdefault('name', 'Unnamed')
    options.setdefault('user', 'John Doe')
    options['email'] = [e for e in options.get('email', '').split(',') if e]
    for email in options['email']:
      if not TryJobBase._EMAIL_VALIDATOR.match(email):
        log.msg("'%s' is an invalid email address!" % email)
        raise BadJobfile("'%s' is an invalid email address!" % email)

    options.setdefault('patch', None)
    options.setdefault('root', None)
    options.setdefault('clobber', False)
    # -pN argument to patch.
    options['patchlevel'] = int(options.get('patchlevel', 0))
    options.setdefault('branch', None)
    options.setdefault('revision', None)
    options.setdefault('reason', '%s: %s' % (options['user'], options['name']))
    options['testfilter'] = [
        i for i in options.get('testfilter', '').split(',') if i
    ]
    options.setdefault('project', self.pools.default_pool_name)
    options.setdefault('repository', None)
    # Code review infos. Enforce numbers.
    def try_int(key):
      if options.setdefault(key, None) is None:
        return
      options[key] = int(options[key])
    try_int('patchset')
    try_int('issue')

    builder_names = []
    if 'bot' in options:
      builder_names = options.get('bot', '').split(',')
    options['bot'] = self.pools.Select(builder_names, options['project'])
    log.msg(
        'Choose %s for job %s' % (','.join(options['bot']), options['reason']))
    return options

  def ParseJob(self, options):
    """Grab try job settings."""
    options = self.parse_options(options)
    # There can be only one to blame per change.
    fake_changes = [
        Change(email, [''], '', revision=options['revision'])
        for email in options['email']
    ]
    patch = None
    if options['patch']:
      patch = (options['patchlevel'], options['patch'], options['root'])
    last_good_url = (self.last_good_urls or {}).get(options['project'])
    code_review_site = (self.code_review_sites or {}).get(options['project'])
    jobstamp = TryJobStamp(
        branch=options['branch'],
        revision=options['revision'],
        patch=patch,
        changes=fake_changes,
        last_good_url=last_good_url,
        code_review_site=code_review_site,
        job_name=options['name'],
        patchset=options['patchset'],
        issue=options['issue'])
    return options['bot'], jobstamp, options['name'], self.get_props(options)

  def get_props(self, options):
    """Current job extra properties that are not related to the source stamp.
    Initialize with the Scheduler's base properties.
    """
    props = Properties()
    props.updateFromProperties(self.properties)
    props.setProperty('clobber', options['clobber'], 'Scheduler')
    if options['testfilter']:
      props.setProperty('testfilters', options['testfilter'], 'Scheduler')
    return props

  def CancelJobsMatching(self, source_stamp, builder_name):
    """Cancels any jobs with the same job and owner."""

    if (not isinstance(source_stamp, TryJobStamp) or
        len(source_stamp.changes) != 1):
      # Not a try job.
      return

    # TODO(maruel): remove once pylint improves its type inference.
    # pylint: disable=E1101
    builder = self.parent.botmaster.builders.get(builder_name, None)
    if not builder:
      # TODO(maruel): Send an email to the user. There's no reference to a
      # mail notifier here.
      return
    # Cancel any pending jobs on this builder that haven't yet started.
    for buildable in builder.buildable:
      if source_stamp.canReplace(buildable.source):
        builder.cancelBuildRequest(buildable)
        log.msg('Canceling job %s on %s' % (source_stamp.job_name,
                                            builder.name))
        break # There should only be one try with a given name.

    # Mark any running builds as canceled. In theory we could cancel these too
    # in practice cancelling might leave the bot in a weird state. Instead we
    # set canceled to true so that after the current step finishes the builder
    # doesn't execute any more steps.
    for build in builder.building:
      for request in build.requests:
        if source_stamp.canReplace(request.source):
          # The request copies the stamp. Set the stamp for both so
          # that the canceled state is reflected in both places.
          build.source.canceled = True
          request.source.canceled = True
          log.msg('Marking %s as canceled on %s' %
                  (source_stamp.job_name, builder_name))

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
    # Send one build request per builder, otherwise the cancelation logic
    # doesn't work.
    build_sets = []
    for builder_name in builder_names:
      build_set = buildset.BuildSet(
          [builder_name],
          jobstamp,
          reason=reason,
          bsid=buildset_id,
          properties=props)
      build_sets.append(build_set)
      self.CancelJobsMatching(build_set, builder_name)
    for build_set in build_sets:
      # Type inference error.
      # pylint: disable=E1101
      self.parent.submitBuildSet(build_set)
    return http.OK
