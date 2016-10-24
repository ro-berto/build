#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Source file for master_utils testcases."""


import unittest

import test_env  # pylint: disable=W0611,W0403

from buildbot.process.properties import Properties
from master import master_utils


def remove_slave(slaves, name):
  for i, s in enumerate(slaves):
    if s.name == name:
      del(slaves[i])
      break
  else:
    assert False, 'slave %s does not exist' % name


class MasterUtilsTest(unittest.TestCase):

  def testPartition(self):
    partitions = master_utils.Partition([(1, 'a'),
                                         (2, 'b'),
                                         (3, 'c'),
                                         ], 2)
    self.assertEquals([['a', 'b'], ['c']], partitions)


class MockBuilder(object):
  def __init__(self, name):
    self.name = name

class MockSlave(object):
  def __init__(self, name, properties):
    self.properties = Properties()
    self.properties.update(properties, "BuildSlave")
    self.properties.setProperty("slavename", name, "BuildSlave")

class MockSlaveBuilder(object):
  def __init__(self, name, properties):
    self.name = name
    self.slave = MockSlave(name, properties)

class PreferredBuilderNextSlaveFuncTest(unittest.TestCase):
  def testNextSlave(self):
    builder1 = MockBuilder('builder1')
    builder2 = MockBuilder('builder2')
    builder3 = MockBuilder('builder3')

    slaves = [
        MockSlaveBuilder('slave1', {'preferred_builder': 'builder1'}),
        MockSlaveBuilder('slave2', {'preferred_builder': 'builder2'}),
        MockSlaveBuilder('slave3', {'preferred_builder': 'builder3'}),
    ]

    f = master_utils.PreferredBuilderNextSlaveFunc()
    self.assertEqual('slave1', f(builder1, slaves).name)
    self.assertEqual('slave2', f(builder2, slaves).name)
    self.assertEqual('slave3', f(builder3, slaves).name)

    remove_slave(slaves, 'slave3')

    # When there is no slave that matches preferred_builder,
    # any slave builder might be chosen.
    self.assertTrue(f(builder3, slaves).name in ['slave1', 'slave2'])

  def testNextSlaveEmpty(self):
    builder = MockBuilder('builder')
    slaves = []

    f = master_utils.PreferredBuilderNextSlaveFunc()

    self.assertIsNone(f(builder, slaves))

  def testNextSlaveNG(self):
    builder1 = MockBuilder('builder1')
    builder2 = MockBuilder('builder2')
    builder3 = MockBuilder('builder3')

    slaves = [
        MockSlaveBuilder('s1', {'preferred_builder': 'builder1'}),
        MockSlaveBuilder('s2', {'preferred_builder': 'builder2'}),
        MockSlaveBuilder('s3', {'preferred_builder': 'builder3'}),
        MockSlaveBuilder('s4', {'preferred_builder': 'builder1'}),
        MockSlaveBuilder('s5', {'preferred_builder': 'builder2'}),
        MockSlaveBuilder('s6', {'preferred_builder': 'builder3'}),
        # Fall-over pool with no preference.
        MockSlaveBuilder('s7', {'preferred_builder': None}),
        MockSlaveBuilder('s8', {'preferred_builder': None}),
    ]

    # Mock random.choice on function return for determinism and to check the
    # full choice range.
    f = lambda builder, slaves: (
        set([s.name for s in master_utils.PreferredBuilderNextSlaveFuncNG(
            choice=list)(builder, slaves)]))

    self.assertEqual(set(['s1', 's4']), f(builder1, slaves))
    self.assertEqual(set(['s2', 's5']), f(builder2, slaves))
    self.assertEqual(set(['s3', 's6']), f(builder3, slaves))

    remove_slave(slaves, 's3')

    # There's still a preferred slave left.
    self.assertEqual(set(['s6']), f(builder3, slaves))

    remove_slave(slaves, 's6')

    # No preferred slave. Slave will be choosen from fall-over pool (i.e.
    # slaves with no preference).
    self.assertEqual(set(['s7', 's8']), f(builder3, slaves))

    # We could also test the case where two slave sets are equal (e.g.
    # removing now 7 and 8), but that'd require making the most_common
    # method deterministic.

    remove_slave(slaves, 's1')
    remove_slave(slaves, 's7')
    remove_slave(slaves, 's8')

    # Now only slaves preferring builder2 have most capacity.
    self.assertEqual(set(['s2', 's5']), f(builder3, slaves))

  def testNextSlaveEmptyNG(self):
    builder = MockBuilder('builder')
    slaves = []

    f = master_utils.PreferredBuilderNextSlaveFuncNG(choice=list)

    self.assertIsNone(f(builder, slaves))

if __name__ == '__main__':
  unittest.main()
