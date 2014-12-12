#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""try_job_rietveld.py testcases."""

import test_env # pylint: disable=unused-import
from common import find_depot_tools # pylint: disable=unused-import

import datetime
import json
import logging
import sys
import unittest
import urlparse
import uuid

from testing_support import auto_stub
from twisted.internet import defer
from twisted.web import client

from master import master_utils
from master import try_job_rietveld
from master.builders_pools import BuildersPools


TEST_BASE_URL = ('https://codereview.chromium.org/get_pending_try_patchsets?'
                 'limit=1000&offset=1&master=tryserver.chromium.linux')
TEST_DUPE_BASE_URL = (
    'https://codereview.chromium.org/get_pending_try_patchsets?'
    'limit=1000&offset=1&master=tryserver.chromium.dupe')


# Create timestamps both with microseconds=0 and !=0.
# See http://crbug.com/380370.
utcnow = datetime.datetime.utcnow()
utcnow_rounded = datetime.datetime(
    utcnow.year, utcnow.month, utcnow.day, utcnow.hour,
    utcnow.minute, utcnow.second)
utcnow_microsec = datetime.datetime(
    utcnow.year, utcnow.month, utcnow.day, utcnow.hour,
    utcnow.minute, utcnow.second, 123456)


TEST_RIETVELD_PAGES = [
  [{'timestamp': datetime.datetime.utcnow(), 'key': 'test_key_1'}],
  [{'timestamp': (utcnow_rounded - datetime.timedelta(hours=5, minutes=59)),
    'key': 'test_key_2'},
   {'timestamp': (utcnow_microsec - datetime.timedelta(hours=6, minutes=1)),
    'key': 'test_key_3'}]
]


TEST_DUPE_RIETVELD_PAGES = [
  [{'timestamp': datetime.datetime.utcnow(), 'key': 'duplicate_key'}],
  [{'timestamp': datetime.datetime.utcnow(), 'key': 'duplicate_key'}],
]


class MockBuildSetsDB(object):

  def __init__(self):
    self._buildset_props = {}

  def addBuildSetProperties(self, bsid, buildset_props):
    self._buildset_props[bsid] = buildset_props

  def getBuildsetProperties(self, bsid):
    return self._buildset_props[bsid]

  def getRecentBuildsets(self, count):
    bsids_desc = sorted(self._buildset_props.keys(), reverse=True)
    return [{'bsid': bsid} for bsid in bsids_desc][:count]


class MockDBCollection(object):

  buildsets = None

  def __init__(self):
    self.buildsets = MockBuildSetsDB()


class MockBotMaster(object):

  def __init__(self):
    self.builders = {}


class MockMaster(object):

  db = None

  def __init__(self):
    self.db = MockDBCollection()
    self.botmaster = MockBotMaster()


class MockTryJobRietveld(object):

  def __init__(self):
    self.submitted_jobs = []

  def SubmitJobs(self, jobs):
    self.submitted_jobs.extend(jobs)
    return defer.succeed(None)

  @staticmethod
  def has_valid_user_list():
    return True

  def addService(self, service):
    pass

  def clear(self):
    self.submitted_jobs = []


class MockValidUserPoller(object):

  mockValid = True
  parent = None

  def __init__(self, interval):
    pass

  @staticmethod
  def contains(_):
    return True

  def valid(self):
    return self.mockValid

  @classmethod
  def setServiceParent(cls, parent):
    cls.parent = parent


class MockRietveldPollerWithCache(object):

  endpoint = None
  parent = None

  def __init__(self, pending_jobs_url, interval):
    MockRietveldPollerWithCache.endpoint = pending_jobs_url

  def poll(self):
    pass

  @classmethod
  def setServiceParent(cls, parent):
    cls.parent = parent


class MockServiceParent(object):

  master = MockMaster()

  def __init__(self):
    pass

  def addService(self, service):
    service.master = self.master


class RietveldPollerWithCacheTest(auto_stub.TestCase):

  def _GetPage(self, url, **_):
    self.assertTrue(url.startswith(TEST_BASE_URL) or
                    url.startswith(TEST_DUPE_BASE_URL))
    self.assertIs(type(url), str)

    self._numRequests += 1

    if url == TEST_BASE_URL:
      cursor = str(uuid.uuid4())
      self._cursors[cursor] = 0
      jobs = TEST_RIETVELD_PAGES[0]
    elif url == TEST_DUPE_BASE_URL:
      cursor = str(uuid.uuid4())
      self._cursors[cursor] = 0
      jobs = TEST_DUPE_RIETVELD_PAGES[0]
    else:
      parsed_url = urlparse.urlparse(url)
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      prev_cursor = parsed_qs.get('cursor', [''])[0]
      self.assertIn(prev_cursor, self._cursors,
                    'Requested incorrect cursor %s. Available cursors: %s' %
                    (prev_cursor, self._cursors))
      if url.startswith(TEST_BASE_URL):
        test_pages = TEST_RIETVELD_PAGES
      elif url.startswith(TEST_DUPE_BASE_URL):
        test_pages = TEST_DUPE_RIETVELD_PAGES
      if self._cursors[prev_cursor] + 1 < len(test_pages):
        cursor = str(uuid.uuid4())
        self._cursors[cursor] = self._cursors[prev_cursor] + 1
        jobs = test_pages[self._cursors[cursor]]
      else:
        cursor = prev_cursor
        jobs = []

    response = {'cursor': cursor, 'jobs': jobs}

    def date_handler(obj):
      if isinstance(obj, datetime.datetime):
        return str(obj)

    response_str = json.dumps(response, default=date_handler)
    return defer.succeed(response_str)

  def setUp(self):
    self.mock(client, 'getPage', self._GetPage)
    self._numRequests = 0
    self._cursors = {}
    self._mockTJR = MockTryJobRietveld()
    self._mockMaster = MockMaster()
    super(RietveldPollerWithCacheTest, self).setUp()

  def testRequestsAllPagesWithJobsFromRietveld(self):
    # pylint: disable=protected-access
    poller = try_job_rietveld._RietveldPollerWithCache(TEST_BASE_URL, 60)
    poller.master = self._mockMaster
    poller.setServiceParent(self._mockTJR)
    poller.poll()
    self.assertEqual(self._numRequests, len(TEST_RIETVELD_PAGES) + 1)

  def testSubmitsNewJobsAndIgnoresOldOnes(self):
    # pylint: disable=protected-access
    poller = try_job_rietveld._RietveldPollerWithCache(TEST_BASE_URL, 60)
    poller.master = self._mockMaster
    poller.setServiceParent(self._mockTJR)
    poller.poll()
    self.assertEqual(len(self._mockTJR.submitted_jobs), 2)
    self.assertEquals(self._mockTJR.submitted_jobs[0]['key'], 'test_key_1')
    self.assertEquals(self._mockTJR.submitted_jobs[1]['key'], 'test_key_2')

  def testSubmitsNewJobsAndIgnoresDuplicateKeys(self):
    # pylint: disable=protected-access
    poller = try_job_rietveld._RietveldPollerWithCache(TEST_DUPE_BASE_URL, 60)
    poller.master = self._mockMaster
    poller.setServiceParent(self._mockTJR)
    poller.poll()
    # This part is critical: we verify only one job is submitted, not two
    # with the same keys.
    self.assertEqual(len(self._mockTJR.submitted_jobs), 1)
    self.assertEquals(self._mockTJR.submitted_jobs[0]['key'], 'duplicate_key')

  def testDoesNotResubmitPreviousJobs(self):
    # pylint: disable=protected-access
    poller = try_job_rietveld._RietveldPollerWithCache(TEST_BASE_URL, 60)
    poller.master = self._mockMaster
    poller.setServiceParent(self._mockTJR)
    poller.poll()
    self._mockTJR.clear()
    poller.poll()
    self.assertEquals(len(self._mockTJR.submitted_jobs), 0)

  def testDoesNotResubmitJobsAlreadyOnMaster(self):
    # pylint: disable=protected-access
    poller = try_job_rietveld._RietveldPollerWithCache(TEST_BASE_URL, 60)
    self._mockMaster.db.buildsets.addBuildSetProperties(
        42, {'try_job_key': ('test_key_1', 'Try bot')})
    poller.master = self._mockMaster
    poller.setServiceParent(self._mockTJR)
    poller.poll()
    self.assertEquals(len(self._mockTJR.submitted_jobs), 1)
    self.assertEquals(self._mockTJR.submitted_jobs[0]['key'], 'test_key_2')

  def testShouldLimitNumberOfBuildsetsUsedForInit(self):
    # pylint: disable=protected-access
    self.mock(try_job_rietveld, 'MAX_RECENT_BUILDSETS_TO_INIT_CACHE', 1)
    poller = try_job_rietveld._RietveldPollerWithCache(TEST_BASE_URL, 60)
    self._mockMaster.db.buildsets.addBuildSetProperties(
        42, {'try_job_key': ('test_key_1', 'Try bot')})
    self._mockMaster.db.buildsets.addBuildSetProperties(
        55, {'try_job_key': ('test_key_2', 'Try bot')})
    poller.master = self._mockMaster
    poller.setServiceParent(self._mockTJR)
    poller.poll()
    self.assertEquals(len(self._mockTJR.submitted_jobs), 1)
    self.assertEquals(self._mockTJR.submitted_jobs[0]['key'], 'test_key_1')

  def testDoesNotPerformPollWhenThereAreNoValidUsers(self):
    # pylint: disable=protected-access
    self.mock(self._mockTJR, 'has_valid_user_list', lambda: False)
    poller = try_job_rietveld._RietveldPollerWithCache(TEST_BASE_URL, 60)
    poller.master = self._mockMaster
    poller.setServiceParent(self._mockTJR)
    poller.poll()
    self.assertEqual(len(self._mockTJR.submitted_jobs), 0)


class TryJobRietveldTest(auto_stub.TestCase):

  def setUp(self):
    self.mock(try_job_rietveld, '_ValidUserPoller', MockValidUserPoller)
    self.mock(try_job_rietveld, '_RietveldPollerWithCache',
              MockRietveldPollerWithCache)
    self.mock(master_utils, 'GetMastername', lambda: 'tryserver.test')
    self.tjr = try_job_rietveld.TryJobRietveld(
        name='test_try_job_rietveld',
        last_good_urls={'test_project': 'http://www.example.com/lkgr'},
        code_review_sites={'test_project': 'http://www.example.com'},
        pools=BuildersPools('test_project'),
        project='test_project',
        filter_master=True)

  def testCorrectlyComputesValidityOfTheUserList(self):
    MockValidUserPoller.mockValid = False
    self.assertFalse(self.tjr.has_valid_user_list())

    MockValidUserPoller.mockValid = True
    self.assertTrue(self.tjr.has_valid_user_list())

  def testCorrectlyFormsTheEndpointForRietveldPoller(self):
    self.assertEqual(MockRietveldPollerWithCache.endpoint,
                     'http://www.example.com/get_pending_try_patchsets'
                     '?limit=1000&master=tryserver.test')

  def testSetsServiceParentOnUserAndRietveldPollers(self):
    mockServiceParent = MockServiceParent()
    self.tjr.setServiceParent(mockServiceParent)
    self.assertEqual(self.tjr, MockValidUserPoller.parent)
    self.assertEqual(self.tjr, MockRietveldPollerWithCache.parent)

  # TODO(sergiyb): Write tests for the SubmitJobs.


if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.WARNING,
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  unittest.main()
