#!/usr/bin/env vpython
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

import mock

import test_env  # pylint: disable=relative-import

import slave.slave_utils as slave_utils
from common import chromium_utils

# build/scripts/slave/unittests
_SCRIPT_DIR = os.path.dirname(__file__)
_BUILD_DIR = os.path.abspath(os.path.join(
    _SCRIPT_DIR, os.pardir, os.pardir))


# Note: The git-svn id / cr pos is intentionally modified.
# Also commit messages modified to be < 80 char.
# TODO(eyaich): Udpate example logs as they are out of date.  Source of truth
# is now git so the git-svn-id entry is no longer present.  Remove BLINK_LOG
# once we remove the blink revision concept
CHROMIUM_LOG = """
Update GPU rasterization device whitelist

This replaces the whitelisting of all Qualcomm GPUs on
Android 4.4 with whitelisting all Android 4.4 devices
with GL ES version >= 3.0.

BUG=405646

Review URL: https://codereview.chromium.org/468103003

Cr-Commit-Position: refs/heads/master@{#291141}
git-svn-id: svn://svn.chromium.org/chrome/trunk/src@291140 0039d316-1c4b-4281
"""

BLINK_LOG = """
[Sheriff-o-matic] Remove race condition on the commit list.

By always modifying the same list of commits, we ensure that data binding

As well, renamed "revisionLog" to "commitLog" everywhere, to better reflect

BUG=405327
NOTRY=true

Review URL: https://codereview.chromium.org/485253004

git-svn-id: svn://svn.chromium.org/blink/trunk@180728 bbb929c8-8fbe-4397-9dbb-9
"""


class TestGetZipFileNames(unittest.TestCase):
  def setUp(self):
    super(TestGetZipFileNames, self).setUp()
    chromium_utils.OverridePlatformName(sys.platform)

  def testNormalBuildName(self):
    (base_name, version_suffix) = slave_utils.GetZipFileNames(
        '', None, None, 123)
    self._verifyBaseName(base_name)
    self.assertEqual('_123', version_suffix)

  def testNormalBuildNameTryBot(self):
    (base_name, version_suffix) = slave_utils.GetZipFileNames(
        'master.tryserver.chromium.linux', 666, None, 123)
    self._verifyBaseName(base_name)
    self.assertEqual('_666', version_suffix)

  def testNormalBuildNameTryBotExtractNoParentBuildNumber(self):
    def dummy():
      slave_utils.GetZipFileNames(
          'master.tryserver.chromium.linux', 666, None, 123, extract=True)
    self.assertRaises(Exception, dummy)

  def testNormalBuildNameTryBotExtractWithParentBuildNumber(self):
    (base_name, version_suffix) = slave_utils.GetZipFileNames(
        'master.tryserver.chromium.linux', 666, 999, 123, extract=True)
    self._verifyBaseName(base_name)
    self.assertEqual('_999', version_suffix)

  def _verifyBaseName(self, base_name):
    self.assertEqual('full-build-%s' % sys.platform, base_name)


class TestGetBuildRevisions(unittest.TestCase):
  def testNormal(self):
    build_revision = slave_utils.GetBuildRevisions(_BUILD_DIR)
    self.assertTrue(build_revision > 0)

  def testWebKitDir(self):
    build_revision = slave_utils.GetBuildRevisions(_BUILD_DIR)
    self.assertTrue(build_revision > 0)

  def testRevisionDir(self):
    build_revision = slave_utils.GetBuildRevisions(
        _BUILD_DIR, revision_dir=_BUILD_DIR)
    self.assertTrue(build_revision > 0)


@mock.patch('__main__.slave_utils.GSUtilSetup',
      mock.MagicMock(side_effect=lambda: ['/mock/gsutil']))
@mock.patch('__main__.chromium_utils.RunCommand')
class TestGSUtil(unittest.TestCase):

  def testGSUtilCopyCacheControl(self,  # pylint: disable=no-self-use
                                 run_command_mock):
    slave_utils.GSUtilCopyFile('foo', 'bar', cache_control='mock_cache')
    run_command_mock.assert_called_with([
      '/mock/gsutil',
      '-h',
      'Cache-Control:mock_cache',
      'cp',
      'file://foo',
      'file://bar/foo',
    ])
    slave_utils.GSUtilCopyDir('foo', 'bar', cache_control='mock_cache')
    run_command_mock.assert_called_with([
      '/mock/gsutil',
      '-m',
      '-h',
      'Cache-Control:mock_cache',
      'cp',
      '-R',
      'foo',
      'bar',
    ])

  def testGSUtilCopyFileWithDestFilename(self, # pylint: disable=no-self-use
                                         run_command_mock):
    slave_utils.GSUtilCopyFile(
        '/my/local/path/foo.txt', 'gs://bucket/dest/dir',
        dest_filename='bar.txt')
    run_command_mock.assert_called_with([
      '/mock/gsutil',
      'cp',
      'file:///my/local/path/foo.txt',
      'gs://bucket/dest/dir/bar.txt',
    ])

  def testGSUtilCopyFileWithQuietFlag(self, # pylint: disable=no-self-use
                                      run_command_mock):
    slave_utils.GSUtilCopyFile('foo', 'bar', add_quiet_flag=True)
    run_command_mock.assert_called_with([
      '/mock/gsutil',
      '-q',
      'cp',
      'file://foo',
      'file://bar/foo',
    ])

  def testGSUtilCopyDirWithQuietFlag(self, #  pylint: disable=no-self-use
                                     run_command_mock):
    slave_utils.GSUtilCopyDir('foo', 'bar', add_quiet_flag=True)
    run_command_mock.assert_called_with([
      '/mock/gsutil',
      '-m',
      '-q',
      'cp',
      '-R',
      'foo',
      'bar',
    ])


class GetGitRevisionTest(unittest.TestCase):
  """Tests related to getting revisions from a directory."""
  def test_GitSvnCase(self):
    # pylint: disable=W0212
    self.assertEqual(slave_utils._GetGitCommitPositionFromLog(CHROMIUM_LOG),
                     '291141')
    # pylint: disable=W0212
    self.assertEqual(slave_utils._GetGitCommitPositionFromLog(BLINK_LOG),
                     '180728')

  def test_GetCommitPosFromBuildPropTest(self):
    """Tests related to getting a commit position from build properties."""
    # pylint: disable=W0212
    self.assertEqual(slave_utils._GetCommitPos(
        {'got_src_revision_cp': 'refs/heads/master@{#12345}'}), 12345)
    # pylint: disable=W0212
    self.assertIsNone(slave_utils._GetCommitPos({'got_revision': 12345}))

class TelemetryRevisionTest(unittest.TestCase):
  def test_GetPerfDashboardRevisions(self):
    point_id = 1470050195
    revision = '294850'
    build_properties = {
      'got_webrtc_revision': None,
      'got_v8_revision': 'undefined',
      'git_revision': '9a7b354',
    }
    versions = slave_utils.GetPerfDashboardRevisions(
        build_properties, revision, point_id)
    self.assertEqual(
        {'rev': '294850', 'git_revision': '9a7b354',
         'point_id': 1470050195},
        versions)


class RemoveTempDirContentsTest(unittest.TestCase):
  """Tests related to removing contents of the temporary directory."""
  def setUp(self):
    self._mock_listdir = None
    self._removed = []
    self._whitelist = []

    mock.patch('sys.argv', self._whitelist).start()
    mock.patch('tempfile.gettempdir', lambda: '/tmp/').start()
    mock.patch('os.listdir', lambda p: self._mock_listdir[p]).start()
    mock.patch('os.path.isdir', lambda p: p.endswith('dir')).start()
    mock.patch('os.path.islink', lambda _: False).start()
    mock.patch('os.remove', self._removed.append).start()
    mock.patch('shutil.rmtree',
               lambda p, *args, **kwargs: self._removed.append(p)).start()

  def tearDown(self):
    mock.patch.stopall()

  def test_DoesntRemoveWhitelisted(self):
    self._mock_listdir = {
        '/tmp': ['1_file', '2_file', '1_dir', '2_dir', '3_dir'],
        '/tmp/1_dir': [],
        '/tmp/2_dir': [],
        '/tmp/3_dir': ['3.1_file', '3.2_file', '3.1_dir', '3.2_dir', '3.3_dir'],
        '/tmp/3_dir/3.1_dir': ['3.1.1_file', '3.1.2_file', '3.1.1_dir'],
        '/tmp/3_dir/3.2_dir': ['3.2.1_file', '3.2.1_dir'],
        '/tmp/3_dir/3.3_dir': [],
    }
    self._whitelist = [
        '/tmp/1_dir',
        '/tmp/1_file',
        '/tmp/3_dir/3.1_dir/3.1.1_file',
        '/tmp/3_dir/3.2_dir',
        '/tmp/3_dir/3.2_file',
    ]

    with mock.patch('sys.argv', self._whitelist):
      slave_utils.RemoveTempDirContents()

    self.assertEqual(
        sorted([
            '/tmp/2_file',
            '/tmp/2_dir',
            '/tmp/3_dir/3.1_dir/3.1.2_file',
            '/tmp/3_dir/3.1_dir/3.1.1_dir',
            '/tmp/3_dir/3.1_file',
            '/tmp/3_dir/3.3_dir'
        ]),
        sorted(self._removed))


if __name__ == '__main__':
  unittest.main()
