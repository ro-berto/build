# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from buildbot.process.properties import Properties
from buildbot.schedulers.trysched import TryBase
from buildbot.schedulers.trysched import BadJobfile
from twisted.internet import defer
from twisted.python import log
from twisted.web import client


class TryJobBase(TryBase):
  compare_attrs = TryBase.compare_attrs + (
      'pools', 'last_good-urls', 'code_review_sites')

  # Simplistic email matching regexp.
  _EMAIL_VALIDATOR = re.compile(
      r'[a-zA-Z][a-zA-Z0-9\.\+\-\_]*@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,3}$')

  def __init__(self, name, pools, properties,
               last_good_urls, code_review_sites):
    TryBase.__init__(self, name, pools.ListBuilderNames(), properties or {})
    self.pools = pools
    pools.SetParent(self)
    self.last_good_urls = last_good_urls
    self.code_review_sites = code_review_sites
    self._last_lkgr = None

  def gotChange(self, change, important):  # pylint: disable=R0201
    log.msg('ERROR: gotChange was unexpectedly called.')

  def parse_options(self, options):
    """Converts try job settings into a dict."""
    try:
      # Flush None and '' keys.
      options = dict(
          (k, v) for k, v in options.iteritems() if v not in (None, ''))

      options.setdefault('name', 'Unnamed')
      options.setdefault('user', 'John Doe')
      options['email'] = [e for e in options.get('email', '').split(',') if e]
      for email in options['email']:
        if not TryJobBase._EMAIL_VALIDATOR.match(email):
          raise BadJobfile("'%s' is an invalid email address!" % email)

      options.setdefault('patch', None)
      options.setdefault('root', None)
      # -pN argument to patch.
      options['patchlevel'] = int(options.get('patchlevel', 0))
      options.setdefault('branch', None)
      options.setdefault('revision', None)
      options.setdefault(
          'reason', '%s: %s' % (options['user'], options['name']))
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
          'Choose %s for job %s' %
          (','.join(options['bot']), options['reason']))
      return options
    except (TypeError, ValueError), e:
      raise BadJobfile('Failed to parse the metadata: %r' % options, e)

  def get_props(self, options):
    """Current job extra properties that are not related to the source stamp.
    Initialize with the Scheduler's base properties.
    """
    keys = ('clobber', 'issue', 'patchset', 'rietveld', 'testfilter')
    # All these settings have no meaning when False or not set, so don't set
    # them in that case.
    properties = dict((i, options[i]) for i in keys if options.get(i))
    props = Properties()
    props.updateFromProperties(self.properties)
    props.update(properties, 'Try job')
    return props

  @staticmethod
  def parse_decoration(properties, decorations):
    """Returns properties extended by the meaning of decoration.
    """

    props = Properties()
    props.updateFromProperties(properties)
    for decoration in decorations.split(':'):
      if decoration == 'compile':
        testfilter = props.getProperty('testfilter') or 'None'
        props.setProperty('testfilter', testfilter, 'Decoration')

      #TODO(petermayo) Define a DSL of useful modifications to individual
      # bots of a test run.
    return props

  def SubmitJob(self, parsed_job, changeids):
    if not parsed_job['bot']:
      raise BadJobfile(
          'incoming Try job did not specify any allowed builder names')

    # Verify the try job patch is not more than 20MB.
    patchsize = len(parsed_job['patch'])
    if patchsize > 20*1024*1024:  # 20MB
      raise BadJobfile('incoming Try job patch is %s bytes, '
                       'must be less than 20MB' % (patchsize))

    d = self.master.db.sourcestamps.addSourceStamp(
        branch=parsed_job['branch'],
        revision=parsed_job['revision'],
        patch_body=parsed_job['patch'],
        patch_level=parsed_job['patchlevel'],
        patch_subdir=parsed_job['root'],
        project=parsed_job['project'],
        repository=parsed_job['repository'] or '',
        changeids=changeids)

    def create_buildset(ssid):
      log.msg('Creating try job(s) %s' % ssid)
      result = None
      for build in parsed_job['bot']:
        bot = build.split(':', 1)[0]
        result = self.addBuildsetForSourceStamp(ssid=ssid,
            reason=parsed_job['name'],
            external_idstring=parsed_job['name'],
            builderNames=[bot],
            properties=self.parse_decoration(
                self.get_props(parsed_job), ''.join(build.split(':', 1)[1:])))
      return result

    d.addCallback(create_buildset)
    d.addErrback(log.err, "Failed to queue a try job!")
    return d

  def get_lkgr(self, options):
    """Grabs last known good revision number if necessary."""
    options['rietveld'] = (self.code_review_sites or {}).get(options['project'])
    last_good_url = (self.last_good_urls or {}).get(options['project'])
    if options['revision'] or not last_good_url:
      return defer.succeed(0)

    def Success(result):
      try:
        new_value = int(result.strip())
      except (TypeError, ValueError):
        new_value = None
      if new_value and (not self._last_lkgr or new_value > self._last_lkgr):
        self._last_lkgr = new_value
      options['revision'] = self._last_lkgr or 'HEAD'

    def Failure(result):
      options['revision'] = self._last_lkgr or 'HEAD'

    connection = client.getPage(last_good_url, agent='buildbot')
    connection.addCallbacks(Success, Failure)
    return connection
