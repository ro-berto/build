#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env  # pylint: disable=W0403,W0611

import json
import StringIO
import unittest
import urllib2
import urllib

from testing_support.super_mox import mox
from testing_support.super_mox import SuperMoxTestBase

import slave.get_swarm_results as swarm_results


RUN_TEST_OUTPUT = (
"""[----------] 2 tests from StaticCookiePolicyTest
[ RUN      ] StaticCookiePolicyTest.AllowAllCookiesTest
[       OK ] StaticCookiePolicyTest.AllowAllCookiesTest (0 ms)
[ RUN      ] StaticCookiePolicyTest.BlockAllCookiesTest
[       OK ] StaticCookiePolicyTest.BlockAllCookiesTest (0 ms)
[----------] 2 tests from StaticCookiePolicyTest (0 ms total)

[----------] 1 test from TCPListenSocketTest
[ RUN      ] TCPListenSocketTest.ServerSend
[       OK ] TCPListenSocketTest.ServerSend (1 ms)
[----------] 1 test from TCPListenSocketTest (1 ms total)
""")

RUN_TEST_OUTPUT_FAILURE = (
"""[----------] 2 tests from StaticCookiePolicyTest
[ RUN      ] StaticCookiePolicyTest.AllowAllCookiesTest
[       OK ] StaticCookiePolicyTest.AllowAllCookiesTest (0 ms)
[ RUN      ] StaticCookiePolicyTest.BlockAllCookiesTest
E:\b\build\slave\win\build\src\chrome\test.cc: error: Value of: result()
  Actual: false
Expected: true
[  FAILED  ] StaticCookiePolicyTest.BlockAllCookiesTest (0 ms)
[----------] 2 tests from StaticCookiePolicyTest (0 ms total)

[----------] 1 test from TCPListenSocketTest
[ RUN      ] TCPListenSocketTest.ServerSend
[       OK ] TCPListenSocketTest.ServerSend (1 ms)
[----------] 1 test from TCPListenSocketTest (1 ms total)
""")

SWARM_OUTPUT_WITHOUT_FAILURE = ("""
[ RUN      ] unittests.Run Test
""" +
RUN_TEST_OUTPUT +
"""[       OK ] unittests.Run Test (2549 ms)
[ RUN      ] unittests.Clean Up
No output!
[       OK ] unittests.Clean Up (6 ms)

[----------] unittests summary
[==========] 2 tests ran. (2556 ms total)
""")

SWARM_OUTPUT_WITH_FAILURE = ("""
[ RUN      ] unittests.Run Test
""" +
RUN_TEST_OUTPUT_FAILURE +
"""[       OK ] unittests.Run Test (2549 ms)
[ RUN      ] unittests.Clean Up
No output!
[       OK ] unittests.Clean Up (6 ms)

[----------] unittests summary
[==========] 2 tests ran. (2556 ms total)
""")

SWARM_OUTPUT_WITH_NO_TEST_OUTPUT = """
Unable to connection to swarm machine.
"""

BUILDBOT_OUTPUT = ("""
================================================================
Begin output from shard index 0 (machine tag: localhost, id: host)
================================================================

""" + RUN_TEST_OUTPUT +
"""
================================================================
End output from shard index 0 (machine tag: localhost, id: host). Return 0
================================================================

Summary for all the shards:
All tests passed.
""")

BUILDBOT_OUTPUT_FAILURE = ("""
================================================================
Begin output from shard index 0 (machine tag: localhost, id: host)
================================================================

""" + RUN_TEST_OUTPUT_FAILURE +
"""
================================================================
End output from shard index 0 (machine tag: localhost, id: host). Return 1
================================================================

Summary for all the shards:
1 test failed, listed below:
  StaticCookiePolicyTest.BlockAllCookiesTest
""")

BUILDBOT_OUTPUT_NO_TEST_OUTPUT = ("""
================================================================
Begin output from shard index 0 (machine tag: localhost, id: host)
================================================================

No output produced by the test, it may have failed to run.
Showing all the output, including swarm specific output.

""" + SWARM_OUTPUT_WITH_NO_TEST_OUTPUT +
"""
================================================================
End output from shard index 0 (machine tag: localhost, id: host). Return 1
================================================================

Summary for all the shards:
All tests passed.
""")



TEST_SHARD_1 = 'Note: This is test shard 1 of 3.'
TEST_SHARD_2 = 'Note: This is test shard 2 of 3.'
TEST_SHARD_3 = 'Note: This is test shard 3 of 3.'


SWARM_SHARD_OUTPUT = ("""
[ RUN      ] unittests.Run Test
%s
[       OK ] unittests.Run Test (2549 ms)
[ RUN      ] unittests.Clean Up
No output!
[       OK ] unittests.Clean Up (6 ms)

[----------] unittests summary
[==========] 2 tests ran. (2556 ms total)
""")

TEST_SHARD_OUTPUT_1 = SWARM_SHARD_OUTPUT % TEST_SHARD_1
TEST_SHARD_OUTPUT_2 = SWARM_SHARD_OUTPUT % TEST_SHARD_2
TEST_SHARD_OUTPUT_3 = SWARM_SHARD_OUTPUT % TEST_SHARD_3

BUILDBOT_SHARD_OUTPUT = ("""
================================================================
Begin output from shard index %d (machine tag: localhost, id: host)
================================================================

%s

================================================================
End output from shard index %d (machine tag: localhost, id: host). Return %d
================================================================
""")

BUILDBOT_OUTPUT_SHARDS = [
    BUILDBOT_SHARD_OUTPUT % (0, TEST_SHARD_1, 0, 0),
    '\nSkipping shard index 1 because it is a repeat of an earlier shard.\n',
    BUILDBOT_SHARD_OUTPUT % (2, TEST_SHARD_2, 2, 0),
    BUILDBOT_SHARD_OUTPUT % (3, TEST_SHARD_3, 3, 0)
]

BUILDBOT_FULL_SHARDED_OUTPUT_WITH_SKIP = '\n'.join(BUILDBOT_OUTPUT_SHARDS) + """
Summary for all the shards:
All tests passed.
"""


def generate_url_response(shard_output, exit_codes):
  response_message = json.dumps(
      {'machine_id': 'host',
       'machine_tag': 'localhost',
       'exit_codes': exit_codes,
       'output': shard_output,
       }
      )

  url_response = urllib2.addinfourl(StringIO.StringIO(response_message),
                                    'mock message', 'host')
  url_response.code = 200
  url_response.msg = 'OK'
  return url_response


class TestRunOutputTest(unittest.TestCase):
  def test_correct_output_success(self):
    self.assertEqual(RUN_TEST_OUTPUT,
                     swarm_results.TestRunOutput(SWARM_OUTPUT_WITHOUT_FAILURE))

  def test_correct_output_failure(self):
    self.assertEqual(RUN_TEST_OUTPUT_FAILURE,
                     swarm_results.TestRunOutput(SWARM_OUTPUT_WITH_FAILURE))


class GetTestKeysTest(SuperMoxTestBase):
  def test_no_keys(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    self.mox.StubOutWithMock(swarm_results.time, 'sleep')

    for _ in range(swarm_results.MAX_RETRY_ATTEMPTS):
      swarm_results.urllib2.urlopen(mox.IgnoreArg()).AndReturn(
          StringIO.StringIO('No matching Test Cases'))
      swarm_results.time.sleep(mox.IgnoreArg())
    self.mox.ReplayAll()

    self.assertEqual([], swarm_results.GetTestKeys('http://host:9001',
                                                   'my_test'))
    expected_output = (swarm_results.MAX_RETRY_ATTEMPTS *
                       'Warning: Unable to find any tests with the name, '
                       'my_test, on swarm server\n')
    expected_output += ('Error: Test keys still not visible after 20 attempts. '
                        'Aborting\n')
    self.checkstdout(expected_output)


    self.mox.VerifyAll()

  def test_no_keys_first_query(self):
    keys = ['keys1', 'keys2']

    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    self.mox.StubOutWithMock(swarm_results.time, 'sleep')
    swarm_results.urllib2.urlopen(mox.IgnoreArg()).AndReturn(
        StringIO.StringIO('No matching Test Cases'))
    swarm_results.time.sleep(mox.IgnoreArg())
    swarm_results.urllib2.urlopen(mox.IgnoreArg()).AndReturn(
        StringIO.StringIO(json.dumps(keys)))
    self.mox.ReplayAll()

    self.assertEqual(keys,
                     swarm_results.GetTestKeys('http://host:9001', 'my_test'))
    self.checkstdout('Warning: Unable to find any tests with the name, '
                     'my_test, on swarm server\n')

    self.mox.VerifyAll()

  def test_find_keys(self):
    keys = ['key_1', 'key_2']

    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    response = StringIO.StringIO(json.dumps(keys))
    swarm_results.urllib2.urlopen(mox.IgnoreArg()).AndReturn(
        response)
    self.mox.ReplayAll()

    self.assertEqual(keys,
                     swarm_results.GetTestKeys('http://host:9001', 'my_test'))

    self.mox.VerifyAll()


class AllShardsRun(unittest.TestCase):
  def testSingleShard(self):
    shard_watcher = swarm_results.ShardWatcher(1)

    self.assertTrue(
        shard_watcher.ShouldProcessShard('run test\n.Done running test'))

    self.assertEqual([], shard_watcher.MissingShards())
    self.assertTrue(shard_watcher.ShardsCompleted())

  def testSingleShardRepeated(self):
    shard_watcher = swarm_results.ShardWatcher(1)

    self.assertTrue(
        shard_watcher.ShouldProcessShard('run test\n.Done running test'))
    self.assertFalse(
        shard_watcher.ShouldProcessShard('run test\n.Done running test'))

    self.assertEqual([], shard_watcher.MissingShards())
    self.assertTrue(shard_watcher.ShardsCompleted())

  def testAllShardsRun(self):
    shard_watcher = swarm_results.ShardWatcher(3)

    self.assertTrue(shard_watcher.ShouldProcessShard(TEST_SHARD_1))
    self.assertTrue(shard_watcher.ShouldProcessShard(TEST_SHARD_2))
    self.assertTrue(shard_watcher.ShouldProcessShard(TEST_SHARD_3))

    self.assertEqual([], shard_watcher.MissingShards())
    self.assertTrue(shard_watcher.ShardsCompleted())

  def testShardRepeatedNoMissing(self):
    shard_watcher = swarm_results.ShardWatcher(3)

    self.assertTrue(shard_watcher.ShouldProcessShard(TEST_SHARD_1))
    self.assertFalse(shard_watcher.ShouldProcessShard(TEST_SHARD_1))
    self.assertTrue(shard_watcher.ShouldProcessShard(TEST_SHARD_2))
    self.assertTrue(shard_watcher.ShouldProcessShard(TEST_SHARD_3))

    self.assertEqual([], shard_watcher.MissingShards())
    self.assertTrue(shard_watcher.ShardsCompleted())

  def testShardRepeatedAndMissing(self):
    shard_watcher = swarm_results.ShardWatcher(3)

    self.assertTrue(shard_watcher.ShouldProcessShard(TEST_SHARD_1))
    self.assertFalse(shard_watcher.ShouldProcessShard(TEST_SHARD_1))
    self.assertFalse(shard_watcher.ShouldProcessShard(TEST_SHARD_1))

    self.assertEqual(['2', '3'], shard_watcher.MissingShards())
    self.assertFalse(shard_watcher.ShardsCompleted())

  def testShardOutOfRange(self):
    shard_watcher = swarm_results.ShardWatcher(1)

    with self.assertRaises(AssertionError):
      shard_watcher.ShouldProcessShard(TEST_SHARD_1)


class GetSwarmResults(SuperMoxTestBase):
  def test_get_swarm_results_success(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')

    url_response = generate_url_response(SWARM_OUTPUT_WITHOUT_FAILURE, '0, 0')
    swarm_results.urllib2.urlopen('http://host:9001/get_result?r=key1'
                                  ).AndReturn(url_response)
    swarm_results.urllib2.urlopen('http://host:9001/cleanup_results',
                                  data=urllib.urlencode({'r': 'key1'})
                                  ).AndReturn(StringIO.StringIO(''))
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', 1, ['key1'])

    self.checkstdout(BUILDBOT_OUTPUT)

    self.mox.VerifyAll()

  def test_get_swarm_results_failure(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')

    url_response = generate_url_response(SWARM_OUTPUT_WITH_FAILURE, '0, 1')
    swarm_results.urllib2.urlopen('http://host:9001/get_result?r=key1'
                                  ).AndReturn(url_response)
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', 1, ['key1'])

    self.checkstdout(BUILDBOT_OUTPUT_FAILURE)

    self.mox.VerifyAll()

  def test_get_swarm_results_no_test_output(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')

    shard_output = json.dumps(
      {'machine_id': 'host',
       'machine_tag': 'localhost',
       'exit_codes': '0, 0',
       'output': SWARM_OUTPUT_WITH_NO_TEST_OUTPUT
     }
    )

    url_response = urllib2.addinfourl(StringIO.StringIO(shard_output),
                                      'mock message', 'host')
    url_response.code = 200
    url_response.msg = 'OK'
    swarm_results.urllib2.urlopen('http://host:9001/get_result?r=key1'
                                  ).AndReturn(url_response)
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', 1, ['key1'])

    self.checkstdout(BUILDBOT_OUTPUT_NO_TEST_OUTPUT)

    self.mox.VerifyAll()

  def test_get_swarm_results_no_keys(self):
    swarm_results.GetSwarmResults('http://host:9001', 1, [])

    self.checkstdout('Error: No test keys to get results with\n')

    self.mox.VerifyAll()

  def test_get_swarm_results_url_errors(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    self.mox.StubOutWithMock(swarm_results.time, 'sleep')
    url = 'http://host:9001/get_result?r=key1'
    exception = urllib2.URLError('failed to connect')

    for i in range(swarm_results.MAX_RETRY_ATTEMPTS):
      swarm_results.urllib2.urlopen(url).AndRaise(exception)
      if i + 1 != swarm_results.MAX_RETRY_ATTEMPTS:
        swarm_results.time.sleep(mox.IgnoreArg())
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', 1, ['key1'])

    expected_output = []
    for _ in range(swarm_results.MAX_RETRY_ATTEMPTS):
      expected_output.append('Error: Calling %s threw %s' % (url, exception))
    expected_output.append(
        'Unable to connect to the given url, %s, after %d attempts. Aborting.' %
        (url, swarm_results.MAX_RETRY_ATTEMPTS))
    expected_output.append('Summary for all the shards:')
    expected_output.append('All tests passed.')
    expected_output.append('Not all shards were executed.')
    expected_output.append('The following gtest shards weren\'t run:')
    expected_output.append('  1')


    self.checkstdout('\n'.join(expected_output) + '\n')

    self.mox.VerifyAll()

  def test_get_swarm_results_all_shards_repeated(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')

    url_response = generate_url_response(SWARM_OUTPUT_WITHOUT_FAILURE, '0, 0')
    keys = ['key1', 'key1-repeat']

    # Only key1 is queried, since after it is recieved we have all the shards
    # we want.
    swarm_results.urllib2.urlopen('http://host:9001/get_result?r=%s' % keys[0]
                                  ).AndReturn(url_response)
    swarm_results.urllib2.urlopen('http://host:9001/cleanup_results',
                                  data=urllib.urlencode({'r': keys[0]})
                                  ).AndReturn(StringIO.StringIO(''))
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', 1, keys)

    self.checkstdout(BUILDBOT_OUTPUT)

    self.mox.VerifyAll()

  def test_get_swarm_results_some_shards_repeated(self):
    """Have shard 1 repeated twice, then shard 2 and 3."""
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')

    keys = ['key1', 'key1-repeat']
    for key in keys:
      swarm_results.urllib2.urlopen(
          'http://host:9001/get_result?r=%s' % key
          ).AndReturn(generate_url_response(TEST_SHARD_OUTPUT_1, '0, 0'))
      swarm_results.urllib2.urlopen('http://host:9001/cleanup_results',
                                    data=urllib.urlencode({'r': key})
                                    ).AndReturn(StringIO.StringIO(''))

    keys.extend(['key2', 'key3'])
    swarm_results.urllib2.urlopen(
        'http://host:9001/get_result?r=%s' % keys[2]
        ).AndReturn(generate_url_response(TEST_SHARD_OUTPUT_2, '0, 0'))
    swarm_results.urllib2.urlopen('http://host:9001/cleanup_results',
                                  data=urllib.urlencode({'r': keys[2]})
                                  ).AndReturn(StringIO.StringIO(''))
    swarm_results.urllib2.urlopen(
        'http://host:9001/get_result?r=%s' % keys[3]
        ).AndReturn(generate_url_response(TEST_SHARD_OUTPUT_3, '0, 0'))
    swarm_results.urllib2.urlopen('http://host:9001/cleanup_results',
                                  data=urllib.urlencode({'r': keys[3]})
                                  ).AndReturn(StringIO.StringIO(''))

    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', 3, keys)

    self.checkstdout(BUILDBOT_FULL_SHARDED_OUTPUT_WITH_SKIP)

    self.mox.VerifyAll()

if __name__ == '__main__':
  unittest.main()
