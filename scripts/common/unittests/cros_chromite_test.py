#!/usr/bin/env python2.7
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit test suite for common.cros_chromite."""

import test_env

import base64
import json
import unittest

from common import cros_chromite


class MockConfigCache(object):
  def __init__(self, data):
    self.data = data

  def Get(self, name, version=None):
    return self.data.get((name, version))


class ChromiteConfigTestCase(unittest.TestCase):


  CHROMITE_CONFIG = {
    '_default': {
      'foo': 'bar',
      'key': 'value',
    },
    'test': {
      'foo': 'baz',
    },
    'parent': {
      'child_configs': [
        {
          'name': 'alice',
          'vm_tests': [
            'test',
          ],
          'hw_tests': [
            'test',
          ],
          'unittests': True,
        },
        {'name': 'bob'}
      ],
    },
    'baremetal-pre-cq': {
      'vm_tests': [
        'test',
      ],
      'hw_tests': [
        'test',
      ],
      'unittests': True,
    },
    'pre-cq-group': {}
  }

  def setUp(self):
    self.config = cros_chromite.ChromiteConfig.FromConfigDict(
        self.CHROMITE_CONFIG)
    self.test = self.config['test']
    self.parent = self.config['parent']
    self.baremetal = self.config['baremetal-pre-cq']
    self.pre_cq_group = self.config['pre-cq-group']

  def testChildren(self):
    self.assertEqual(len(self.test.children), 0)
    self.assertEqual(len(self.parent.children), 2)
    self.assertEqual(self.parent.children[0]['name'], 'alice')
    self.assertEqual(self.parent.children[1]['name'], 'bob')

  def testDefaultFallthrough_UsesLocalWhenAvailable(self):
    self.assertEqual(self.test['foo'], 'baz')

  def testDefaultFallthrough_UsesDefaultWhenMissing(self):
    self.assertEqual(self.test['key'], 'value')

  def testDefaultFallthrough_UsesFirstChild(self):
    self.assertEqual(self.parent['vm_tests'], ['test'])

  def testHasTests(self):
    self.assertFalse(self.test.HasVmTests())
    self.assertFalse(self.test.HasHwTests())
    self.assertFalse(self.test.HasUnitTests())

    self.assertTrue(self.baremetal.HasVmTests())
    self.assertTrue(self.baremetal.HasHwTests())
    self.assertTrue(self.baremetal.HasUnitTests())

  def testHasTests_DetectsInChildren(self):
    self.assertTrue(self.parent.HasVmTests())
    self.assertTrue(self.parent.HasHwTests())
    self.assertTrue(self.baremetal.HasUnitTests())

  def testPreCqDetection(self):
    self.assertFalse(self.test.IsPreCqBuilder())

    self.assertTrue(self.baremetal.IsPreCqBuilder())
    self.assertFalse(self.baremetal.IsGeneralPreCqBuilder())

    self.assertTrue(self.pre_cq_group.IsPreCqBuilder())
    self.assertTrue(self.pre_cq_group.IsGeneralPreCqBuilder())


class ChromitePinManagerTestCase(unittest.TestCase):

  def testGetPinnedBranch_PinnedBranchReturnsPinnedValue(self):
    pm = cros_chromite.ChromitePinManager(pinned={'a': 'b'}, require=True)
    self.assertEqual(pm.GetPinnedBranch('a'), 'b')

  def testGetPinnedBranch_UnpinnedBranchReturnsBranch(self):
    pm = cros_chromite.ChromitePinManager(pinned={'a': 'b'}, require=False)
    self.assertEqual(pm.GetPinnedBranch('foo'), 'foo')

  def testGetPinnedBranch_UnpinnedBranchReturnsErrorWithRequiredPinning(self):
    pm = cros_chromite.ChromitePinManager(pinned={'a': 'b'}, require=True)
    self.assertRaises(cros_chromite.ChromiteError,
        pm.GetPinnedBranch, 'foo')


class ChromiteConfigManagerTestCase(unittest.TestCase):

  def setUp(self):
    self.cache = MockConfigCache({
      ('test', 'v1'): '{}',
      ('test', 'v_invalid'): '{NOT JSON}',
    })

  def testGetConfig_ValidSucceeds(self):
    manager = cros_chromite.ChromiteConfigManager(self.cache,
        cros_chromite.ChromitePinManager({'test': 'v1'}))
    self.assertTrue(isinstance(manager.GetConfig('test'),
        cros_chromite.ChromiteConfig))

  def testGetConfig_InvalidJsonRaises(self):
    manager = cros_chromite.ChromiteConfigManager(self.cache,
        cros_chromite.ChromitePinManager({'test': 'v_invalid'}))
    self.assertRaises(cros_chromite.ChromiteError, manager.GetConfig, 'test')

  def testGetConfig_MissingRaises(self):
    manager = cros_chromite.ChromiteConfigManager(self.cache)
    self.assertRaises(cros_chromite.ChromiteError, manager.GetConfig, 'foo')


class ChromiteFetcherTestCase(unittest.TestCase):

  def setUp(self):
    self.fetcher = cros_chromite.ChromiteFetcher(
        cros_chromite.ChromitePinManager({'test': 'v1'})
    )

  @staticmethod
  def _configUrlForBranch(branch):
    return '%s/+/%s/%s?format=text' % (
        cros_chromite.ChromiteFetcher.CHROMITE_GITILES_BASE,
        branch,
        cros_chromite.ChromiteFetcher.CHROMITE_CONFIG_PATH,
    )

  def testFetch_Valid(self):
    fetched_urls = []
    def _MockGetText(url):
      fetched_urls.append(url)
      return base64.b64encode('content')
    self.fetcher._GetText = _MockGetText

    data = self.fetcher('test', None)
    self.assertEqual(data, ('content', 'v1'))
    self.assertEqual(fetched_urls, [self._configUrlForBranch('v1')])

  def testFetch_NotBase64(self):
    def _MockGetText(_url):
      return 'Not Valid Base64'
    self.fetcher._GetText = _MockGetText
    self.assertRaises(cros_chromite.GitilesError, self.fetcher, 'test', None)


if __name__ == '__main__':
  unittest.main()
