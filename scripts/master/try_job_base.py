# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

import buildbot
from buildbot.process.properties import Properties

from twisted.python import log

buildbot_0_8 = int(buildbot.version.split('.')[1]) >= 8
if buildbot_0_8:
  from master.try_job_base_bb8 import BadJobfile, TryBase, TryJobBaseMixIn
else:
  from master.try_job_base_bb7 import BadJobfile, TryBase, TryJobBaseMixIn


class TryJobBase(TryBase, TryJobBaseMixIn):
  # 0.7.12 uses list and 0.8.x uses tuple...
  compare_attrs = tuple(list(TryBase.compare_attrs) + [
      'pools', 'last_good-urls', 'code_review_sites'])

  # Simplistic email matching regexp.
  _EMAIL_VALIDATOR = re.compile(
      r'[a-zA-Z][a-zA-Z0-9\.\+\-\_]*@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,3}$')

  def __init__(self, name, pools, properties,
               last_good_urls, code_review_sites):
    # pylint has a false positive: it thinks base constructors aren't called.
    # pylint: disable=W0231
    TryBase.__init__(self, name, pools.ListBuilderNames(), properties or {})
    TryJobBaseMixIn.__init__(self)
    self.pools = pools
    pools.SetParent(self)
    self.last_good_urls = last_good_urls
    self.code_review_sites = code_review_sites

  def gotChange(self, change, important):  # pylint: disable=R0201
    log.msg('ERROR: gotChange was unexpectedly called.')

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
        raise BadJobfile("'%s' is an invalid email address!" % email)

    options.setdefault('patch', None)
    options.setdefault('root', None)
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
