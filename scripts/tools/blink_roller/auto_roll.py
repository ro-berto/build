#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import os.path
import re
import subprocess
import sys
import textwrap
import urllib2


# FIXME: This happens to be where my checkouts are. Since this script
# lives in build, I don't know of a good way to find these automatically.
DEPOT_TOOLS_ROOT = '/src/depot_tools'
CHROMIUM_ROOT = '/src/chromium/src'

sys.path.insert(0, DEPOT_TOOLS_ROOT)
import rietveld


class SheriffCalendar(object):
  BLINK_SHERIFF_URL = \
    'http://build.chromium.org/p/chromium.webkit/sheriff_webkit.js'
  CHROMIUM_SHERIFF_URL = \
    'http://build.chromium.org/p/chromium.webkit/sheriff.js'

  # FIXME: This is only @classmethod and not private to appease pylint.
  @classmethod
  def complete_email(cls, name):
    if '@' not in name:
      return name + '@chromium.org'
    return name

  # FIXME: This is only @classmethod and not private to appease pylint.
  @classmethod
  def names_from_sheriff_js(cls, sheriff_js):
    match = re.match(r'document.write\(\'(.*)\'\)', sheriff_js)
    emails_string = match.group(1)
    # Detect 'none (channel is sheriff)' text and ignore it.
    if 'channel is sheriff' in emails_string.lower():
      return []
    return map(str.strip, emails_string.split(','))

  def _emails_from_url(self, sheriff_url):
    # FIXME: We should be more careful trusting the emails which
    # we pulled from an http url and are passing to the shell!
    sheriff_js = urllib2.urlopen(sheriff_url).read()
    return map(self.complete_email, self._names_from_sheriff_js(sheriff_js))

  def current_gardener_emails(self):
    return self._emails_from_url(self.BLINK_SHERIFF_URL)

  def current_sheriff_emails(self):
    return self._emails_from_url(self.CHROMIUM_SHERIFF_URL)


class AutoRoller(object):
  RIETVELD_URL = 'https://codereview.chromium.org'
  RIETVELD_EMAIL = 'eseidel@chromium.org'
  RIETVELD_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
  ROLL_TIME_LIMIT = datetime.timedelta(hours=24)
  STOP_NAG_TIME_LIMIT = datetime.timedelta(hours=12)
  ADMIN_EMAIL = 'eseidel@chromium.org'

  # FIXME: These regexps are not ready for Git revisions:
  ROLL_DESCRIPTION_REGEXP = \
    r'Blink roll (?P<from_revision>\d+):(?P<to_revision>\d+)'

  # FIXME: These are taken from gardeningserver.py and should be shared.
  CHROMIUM_SVN_DEPS_URL = 'http://src.chromium.org/chrome/trunk/src/DEPS'
  # 'webkit_revision': '149598',
  BLINK_REVISION_REGEXP = \
    re.compile(r'^  "webkit_revision": "(?P<revision>\d+)",$', re.MULTILINE)

  ROLL_BOT_INSTRUCTIONS = textwrap.dedent(
    '''This roll was created by the Blink AutoRollBot.
    http://www.chromium.org/blink/blinkrollbot''')

  PLEASE_RESUME_NAG = textwrap.dedent('''
    Rollbot was stopped by the presence of 'STOP' in an earlier comment.
    The last update to this issue was over %(stop_nag_timeout)s hours ago.
    Please close this issue as soon as possible to allow the bot to continue.

    Please email (%(admin)s) if the Rollbot is causing trouble.
    ''' % {'admin': ADMIN_EMAIL, 'stop_nag_timeout': STOP_NAG_TIME_LIMIT})

  def __init__(self):
    self._rietveld = rietveld.Rietveld(
      self.RIETVELD_URL, self.RIETVELD_EMAIL, None)
    self._cached_last_roll_revision = None

  def _parse_time(self, time_string):
    return datetime.datetime.strptime(time_string, self.RIETVELD_TIME_FORMAT)

  def _url_for_issue(self, issue_number):
    return '%s/%d/' % (self.RIETVELD_URL, issue_number)

  def _search_for_active_roll(self):
    # FIXME: Rietveld.search is broken, we should use closed=False
    # but that sends closed=1, we want closed=3.  Using closed=2
    # to that search translates it correctly to closed=3 internally.
    # https://code.google.com/p/chromium/issues/detail?id=242628
    for result in self._rietveld.search(owner=self.RIETVELD_EMAIL, closed=2):
      if result['subject'].startswith('Blink roll'):
        return result
    return None

  def _rollbot_should_stop(self, issue):
    issue_number = issue['issue']
    for message in issue['messages']:
      if 'STOP' in message['text']:
        last_modified = self._parse_time(issue['modified'])
        time_since_last_comment = datetime.datetime.utcnow() - last_modified
        if time_since_last_comment > self.STOP_NAG_TIME_LIMIT:
          self._rietveld.add_comment(issue_number, self.PLEASE_RESUME_NAG)

        print '%s: Rollbot was stopped by %s on at %s, waiting.' % (
          self._url_for_issue(issue_number), message['sender'], message['date'])
        return True
    return False

  def _close_issue(self, issue_number, message=None):
    print 'Closing %s with message: \'%s\'' % (
      self._url_for_issue(issue_number), message)
    if message:
      self._rietveld.add_comment(issue_number, message)
    self._rietveld.close_issue(issue_number)

  @classmethod
  def _path_from_chromium_root(cls, *components):
    assert os.pardir not in components
    return os.path.join(CHROMIUM_ROOT, *components)

  def _last_roll_revision(self):
    if not self._cached_last_roll_revision:
      deps_contents = subprocess.check_output([
        'svn', 'cat', self.CHROMIUM_SVN_DEPS_URL])
      match = re.search(self.BLINK_REVISION_REGEXP, deps_contents)
      self._cached_last_roll_revision = int(match.group('revision'))
    return self._cached_last_roll_revision

  # FIXME: This is largely taken from scm/git.py:
  def _current_svn_revision(self):
    # We use '--grep=' + foo rather than '--grep', foo because
    # git 1.7.0.4 (and earlier) didn't support the separate arg.
    blink_git_dir = \
      self._path_from_chromium_root('third_party', 'WebKit', '.git')
    git_log_args = \
      ['git', '--git-dir', blink_git_dir, 'log', '-1', '--grep=git-svn-id:']
    git_log = subprocess.check_output(git_log_args)
    match = re.search('^\s*git-svn-id:.*@(?P<svn_revision>\d+)\ ',
      git_log, re.MULTILINE)
    return int(match.group('svn_revision'))

  @classmethod
  def _emails_to_cc_on_rolls(cls):
    calendar = SheriffCalendar()
    emails = []
    gardener_emails = calendar.current_gardener_emails()
    if gardener_emails:
      emails.extend(gardener_emails)
    # We could CC the chromium sheriffs if they would like.
    # sheriff_emails = calendar.current_sheriff_emails()
    # if sheriff_emails:
    #     emails.extend(sheriff_emails)
    return emails

  def _start_roll(self, new_roll_revision):
    safely_roll_path = \
      self._path_from_chromium_root('tools', 'safely-roll-blink.py')
    safely_roll_args = [safely_roll_path, new_roll_revision]

    emails = self._emails_to_cc_on_rolls()
    if emails:
      safely_roll_args.extend(['--cc', ','.join(emails)])
    subprocess.check_call(map(str, safely_roll_args))

    # FIXME: It's easier to pull the issue id from rietveld rather than
    # parse it from the safely-roll-blink output.  Once we inline
    # safely-roll-blink into this script this can go away.
    search_result = self._search_for_active_roll()
    self._rietveld.add_comment(search_result['issue'],
      self.ROLL_BOT_INSTRUCTIONS)

  def _validate_active_roll(self, issue):
    issue_number = issue['issue']

    # If the CQ failed, this roll is DOA.
    if not issue['commit']:
      self._close_issue(issue_number,
        'No longer marked for the CQ. Closing, will open a new roll.')
      return False

    create_time = self._parse_time(issue['created'])
    time_since_roll = datetime.datetime.utcnow() - create_time
    print '%s started %s ago' % (
      self._url_for_issue(issue_number), time_since_roll)
    if time_since_roll > self.ROLL_TIME_LIMIT:
      self._close_issue(issue_number,
        'Giving up on this roll after %s. Closing, will open a new roll.' %
        self.ROLL_TIME_LIMIT)
      return False

    last_roll_revision = self._last_roll_revision()
    match = re.match(self.ROLL_DESCRIPTION_REGEXP, issue['description'])
    if int(match.group('from_revision')) != last_roll_revision:
      self._close_issue(issue_number,
        'DEPS has already rolled to %s. Closing, will open a new roll.' %
        last_roll_revision)
      return False

    return True

  def main(self):
    search_result = self._search_for_active_roll()
    issue_number = search_result['issue'] if search_result else None
    if issue_number:
      issue = self._rietveld.get_issue_properties(issue_number, messages=True)
    else:
      issue = None

    if issue:
      if self._rollbot_should_stop(issue):
        return 1  # Should sleep here.
      if not self._validate_active_roll(issue):
        # Don't need to sleep here, but need to return to let the outer script
        # update the checkout.
        return 1
      print '%s is still active, nothing to do.' % \
        self._url_for_issue(issue_number)
      return 0

    last_roll_revision = self._last_roll_revision()
    new_roll_revision = self._current_svn_revision()
    if new_roll_revision <= last_roll_revision:
      print 'ERROR: Already at %d refusing to roll backwards to %d.' % (
        last_roll_revision, new_roll_revision)
      return 1  # Would sleep here.

    self._start_roll(new_roll_revision)
    return 0  # Would sleep here.


if __name__ == '__main__':
  sys.exit(AutoRoller().main())
