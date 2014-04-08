#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import datetime
import unittest

import auto_roll

# auto_roll.py imports find_depot_tools.
from testing_support.super_mox import SuperMoxTestBase


# pylint: disable=W0212


class SheriffCalendarTest(unittest.TestCase):

  def test_complete_email(self):
    calendar = auto_roll.SheriffCalendar()
    expected_emails = ['foo@chromium.org', 'bar@google.com', 'baz@chromium.org']
    names = ['foo', 'bar@google.com', 'baz']
    self.assertEqual(map(calendar.complete_email, names), expected_emails)

  def test_emails(self):
    expected_emails = ['foo@bar.com', 'baz@baz.com']
    calendar = auto_roll.SheriffCalendar()
    calendar._emails_from_url = lambda urls: expected_emails
    self.assertEqual(calendar.current_gardener_emails(), expected_emails)
    self.assertEqual(calendar.current_sheriff_emails(), expected_emails)

  def _assert_parse(self, js_string, expected_emails):
    calendar = auto_roll.SheriffCalendar()
    self.assertEqual(
      calendar.names_from_sheriff_js(js_string), expected_emails)

  def test_names_from_sheriff_js(self):
    self._assert_parse('document.write(\'none (channel is sheriff)\')', [])
    self._assert_parse('document.write(\'foo, bar\')', ['foo', 'bar'])


class AutoRollTest(SuperMoxTestBase):

  TEST_PROJECT = 'test_project'
  TEST_AUTHOR = 'test_author@chromium.org'
  PATH_TO_CHROME = '.'

  DATETIME_FORMAT = '%d-%d-%d %d:%d:%d.%d'
  CURRENT_DATETIME = (2014, 4, 1, 14, 57, 21, 01)
  RECENT_ISSUE_CREATED = (2014, 4, 1, 13, 57, 21, 01)
  OLD_ISSUE_CREATED = (2014, 2, 1, 13, 57, 21, 01)
  CURRENT_DATETIME_STR = DATETIME_FORMAT % CURRENT_DATETIME
  RECENT_ISSUE_CREATED_STR = DATETIME_FORMAT % RECENT_ISSUE_CREATED
  OLD_ISSUE_CREATED_STR = DATETIME_FORMAT % OLD_ISSUE_CREATED

  class MockHttpRpcServer(object):
    def __init__(self, *args, **kwargs):
      pass

  class MockDateTime(datetime.datetime):
    @classmethod
    def utcnow(cls):
      return AutoRollTest.MockDateTime(*AutoRollTest.CURRENT_DATETIME)

  class MockFile(object):
    def __init__(self, contents):
      self._contents = contents

    def read(self):
      return self._contents

  def setUp(self):
    SuperMoxTestBase.setUp(self)
    self.mox.StubOutWithMock(auto_roll.rietveld.Rietveld, 'add_comment')
    self.mox.StubOutWithMock(auto_roll.rietveld.Rietveld, 'close_issue')
    self.mox.StubOutWithMock(auto_roll.rietveld.Rietveld,
                             'get_issue_properties')
    self.mox.StubOutWithMock(auto_roll.rietveld.Rietveld, 'search')
    self.mox.StubOutWithMock(auto_roll.subprocess, 'check_call')
    self.mox.StubOutWithMock(auto_roll.subprocess, 'check_output')
    self.mox.StubOutWithMock(auto_roll.urllib2, 'urlopen')
    auto_roll.datetime.datetime = self.MockDateTime
    auto_roll.rietveld.upload.HttpRpcServer = self.MockHttpRpcServer
    self._arb = auto_roll.AutoRoller(self.TEST_PROJECT,
                                     self.TEST_AUTHOR,
                                     self.PATH_TO_CHROME)

  def _make_issue(self, created_datetime=None):
    return {
        'author': self.TEST_AUTHOR,
        'commit': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'created': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'description': 'Test_Project roll 1234:1235',
        'issue': 1234567,
        'messages': [],
        'modified': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'subject': 'Test_Project roll 1234:1235',
    }

  def test_should_stop(self):
    issue = self._make_issue(created_datetime=self.OLD_ISSUE_CREATED_STR)
    issue['messages'].append({
        'text': 'STOP',
        'sender': self.TEST_AUTHOR,
        'date': '2014-3-31 13:57:21.01'
    })
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    self._arb._rietveld.add_comment(issue['issue'], '''
Rollbot was stopped by the presence of 'STOP' in an earlier comment.
The last update to this issue was over 12:00:00 hours ago.
Please close this issue as soon as possible to allow the bot to continue.

Please email (eseidel@chromium.org) if the Rollbot is causing trouble.
''')

    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 1)
    self.checkstdout('https://codereview.chromium.org/%d/: Rollbot was '
                     'stopped by test_author@chromium.org on at 2014-3-31 '
                     '13:57:21.01, waiting.\n' % issue['issue'])

  def test_already_rolling(self):
    issue = self._make_issue()
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    deps_content = '''
vars = {
  "test_project_revision": "1234",
}
'''
    auto_roll.subprocess.check_output(
        ['svn', 'cat', self._arb.CHROMIUM_SVN_DEPS_URL]).AndReturn(deps_content)
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)
    self.checkstdout('https://codereview.chromium.org/%d/ started %s ago\n'
                     'https://codereview.chromium.org/%d/ is still active, '
                     'nothing to do.\n'
                     % (issue['issue'], '0:59:59.900001', issue['issue']))

  def test_old_issue(self):
    issue = self._make_issue(created_datetime=self.OLD_ISSUE_CREATED_STR)
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    comment_str = ('Giving up on this roll after 1 day, 0:00:00. Closing, will '
                   'open a new roll.')
    self._arb._rietveld.add_comment(issue['issue'], comment_str)
    self._arb._rietveld.close_issue(issue['issue'])
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 1)
    self.checkstdout('https://codereview.chromium.org/%d/ started %s ago\n'
                     'Closing https://codereview.chromium.org/%d/ with message:'
                     ' \'%s\'\n'
                     % (issue['issue'], '59 days, 0:59:59.900001',
                        issue['issue'], comment_str))

  def test_failed_cq(self):
    issue = self._make_issue()
    issue['commit'] = False
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    comment_str = 'No longer marked for the CQ. Closing, will open a new roll.'
    self._arb._rietveld.add_comment(issue['issue'], comment_str)
    self._arb._rietveld.close_issue(issue['issue'])
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 1)
    self.checkstdout('Closing https://codereview.chromium.org/%d/ with message:'
                     ' \'%s\'\n' % (issue['issue'], comment_str))

  def test_no_roll_backwards(self):
    self._arb._rietveld.search(owner=self.TEST_AUTHOR, closed=2).AndReturn([])
    deps_content = '''
vars = {
  "test_project_revision": "1234",
}
'''
    auto_roll.subprocess.check_output(
        ['svn', 'cat', self._arb.CHROMIUM_SVN_DEPS_URL]).AndReturn(deps_content)
    auto_roll.subprocess.check_call(
        ['git', '--git-dir', './third_party/test_project/.git', 'fetch'])
    git_log = '''
commit abcde
Author: Test Author <test_author@example.com>
Date:   Wed Apr 2 14:00:14 2014 -0400

    Make some changes.

    git-svn-id: svn://svn.url/trunk@1231 abcdefgh-abcd-abcd-abcd-abcdefghijkl
'''
    auto_roll.subprocess.check_output(
        ['git', '--git-dir', './third_party/test_project/.git', 'show', '-s',
         'origin/master']).AndReturn(git_log)
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 1)
    self.checkstdout('ERROR: Already at 1234 refusing to roll backwards to '
                     '1231.\n')

  def test_upload_issue(self):
    self._arb._rietveld.search(owner=self.TEST_AUTHOR, closed=2).AndReturn([])
    deps_content = '''
vars = {
  "test_project_revision": "1234",
}
'''
    auto_roll.subprocess.check_output(
        ['svn', 'cat', self._arb.CHROMIUM_SVN_DEPS_URL]).AndReturn(deps_content)
    auto_roll.subprocess.check_call(
        ['git', '--git-dir', './third_party/test_project/.git', 'fetch'])
    git_log = '''
commit abcde
Author: Test Author <test_author@example.com>
Date:   Wed Apr 2 14:00:14 2014 -0400

    Make some changes.

    git-svn-id: svn://svn.url/trunk@1236 abcdefgh-abcd-abcd-abcd-abcdefghijkl
'''
    auto_roll.subprocess.check_output(
        ['git', '--git-dir', './third_party/test_project/.git', 'show', '-s',
         'origin/master']).AndReturn(git_log)
    sheriff_webkit_contents = 'document.write(\'test_sheriff@example.com\')'
    auto_roll.urllib2.urlopen(
        'http://build.chromium.org/p/chromium.webkit/sheriff_webkit.js'
        ).AndReturn(self.MockFile(sheriff_webkit_contents))
    auto_roll.subprocess.check_call(
        ['./tools/safely-roll-deps.py', self.TEST_PROJECT, '1236', '--message',
         'Test_Project roll 1234:1236', '--cc', 'test_sheriff@example.com'])
    issue = self._make_issue(self.CURRENT_DATETIME_STR)
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn([issue])
    self._arb._rietveld.add_comment(issue['issue'],
                                    self._arb.ROLL_BOT_INSTRUCTIONS)
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)


if __name__ == '__main__':
  unittest.main()
