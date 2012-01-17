# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import traceback
import sys

from buildbot.process.properties import Properties
from buildbot.schedulers.trysched import TryBase
from buildbot.schedulers.trysched import BadJobfile
from twisted.internet import defer
from twisted.python import log
from twisted.web import client


def text_to_dict(text):
  """Converts a series of key=value lines in a string into a multi-value dict.
  """
  parsed = {}
  matches = (re.match(r'([A-Z\-\_]+)\=(.+)\w*$', i) for i in text.splitlines())
  for match in filter(None, matches):
    parsed.setdefault(match.group(1), []).append(match.group(2))
  return parsed


def flatten(options, key, default):
  """Expects only one value."""
  if options.setdefault(key, []) == []:
    options[key] = default
  elif len(options[key]) == 1:
    options[key] = options[key][0]
  else:
    raise ValueError('Expecting one value, got many', key, options[key])


def try_int(options, key, default):
  """Expects a int."""
  flatten(options, key, default)
  if options[key] != default:
    options[key] = int(options[key])


def comma_separated(options, key):
  """Splits comma separated strings into multiple values."""
  for i in options.setdefault(key, [])[:]:
    if ',' in i:
      options[key].remove(i)
      options[key].extend(x for x in i.split(',') if x)


def dict_comma(values):
  """Splits comma separated strings with : to create a dict."""
  out = {}
  # See the unit test to understand all the supported formats. It's insane
  # for now.
  for value in values:
    for item in value.split(','):
      if ':' in item:
        bot, test = item.split(':', 1)
        out.setdefault(bot, []).extend(test.split(','))
      else:
        out.setdefault(item, [])
  return out


def parse_options(options, pools):
  """Converts try job settings into a dict.

  The dict is received as dict(str, list(str)).
  """
  try:
    # Flush empty values.
    options = dict((k, v) for k, v in options.iteritems() if v)

    flatten(options, 'name', 'Unnamed')
    flatten(options, 'user', 'John Doe')

    comma_separated(options, 'email')
    for email in options['email']:
      # Access to a protected member XXX of a client class
      # pylint: disable=W0212
      if not TryJobBase._EMAIL_VALIDATOR.match(email):
        raise BadJobfile("'%s' is an invalid email address!" % email)

    flatten(options, 'patch', None)
    flatten(options, 'root', None)
    try_int(options, 'patchlevel', 0)
    flatten(options, 'branch', None)
    flatten(options, 'revision', None)
    flatten(options, 'reason', '%s: %s' % (options['user'], options['name']))

    flatten(options, 'project', pools.default_pool_name if pools else None)
    flatten(options, 'repository', None)

    # Code review info. Enforce numbers.
    try_int(options, 'patchset', None)
    try_int(options, 'issue', None)

    # Manages bot selection and test filtering. It is preferable to use
    # multiple BOT=foo lines
    # Create a dict out of it.
    options['bot'] = dict_comma(options.get('bot', []))
    if not options['bot'] and pools:
      options['bot'] = pools.Select(None, options['project'])
    if not options['bot']:
      raise BadJobfile('No builder selected')
    comma_separated(options, 'testfilter')
    if options['testfilter']:
      for k in options['bot']:
        options['bot'][k].extend(options['testfilter'])

    log.msg(
        'Chose %s for job %s' %
        (','.join(options['bot']), options['reason']))
    return options
  except (TypeError, ValueError), e:
    lines = [
        (i[0].rsplit('/', 1)[-1], i[1])
        for i in traceback.extract_tb(sys.exc_info()[2])
    ]
    raise BadJobfile('Failed to parse the metadata: %r' % options, e, lines)


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
    return parse_options(options, self.pools)

  def get_props(self, builder, options):
    """Current job extra properties that are not related to the source stamp.
    Initialize with the Scheduler's base properties.
    """
    keys = ('clobber', 'issue', 'patchset', 'rietveld')
    # All these settings have no meaning when False or not set, so don't set
    # them in that case.
    properties = dict((i, options[i]) for i in keys if options.get(i))
    properties['testfilter'] = options['bot'].get(builder, None)
    props = Properties()
    props.updateFromProperties(self.properties)
    props.update(properties, 'Try job')
    return props

  def SubmitJob(self, parsed_job, changeids):
    if not parsed_job['bot']:
      raise BadJobfile(
          'incoming Try job did not specify any allowed builder names')

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
      for builder in parsed_job['bot']:
        result = self.addBuildsetForSourceStamp(ssid=ssid,
            reason=parsed_job['name'],
            external_idstring=parsed_job['name'],
            builderNames=[builder],
            properties=self.get_props(builder, parsed_job))
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
