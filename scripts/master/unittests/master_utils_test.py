#!/usr/bin/env vpython
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Source file for master_utils testcases."""


import unittest

import test_env  # pylint: disable=relative-import

from buildbot.buildslave import BuildSlave
from buildbot.process.properties import Properties
from master import master_utils
from master.autoreboot_buildslave import AutoRebootBuildSlave

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

  def testAutoSetupSlaves(self):
    def B(name, slavenames, auto_reboot):
      return {
        'name': name,
        'slavenames': slavenames,
        'auto_reboot' : auto_reboot,
      }
    builders = [
      # Bot sharing two slaves.
      B('B1', ['S1', 'S2'], True),
      B('B2', ['S3', 'S4'], False),
      # Slave sharing two bots.
      B('B3', ['S5'], True),
      B('B4', ['S5'], False),
      # Slave sharing two bots (inverse auto-reboot).
      B('B5', ['S6'], False),
      B('B6', ['S6'], True),
      # Two builders heterogeneously sharing one slave.
      B('B7', ['S7'], True),
      B('B8', ['S7', 'S8'], False),
    ]
    slaves = dict(
      (slave.slavename, slave)
      for slave in master_utils.AutoSetupSlaves(builders, 'pwd')
    )
    self.assertTrue(isinstance(slaves['S1'], AutoRebootBuildSlave))
    self.assertTrue(isinstance(slaves['S2'], AutoRebootBuildSlave))
    self.assertFalse(isinstance(slaves['S3'], AutoRebootBuildSlave))
    self.assertFalse(isinstance(slaves['S4'], AutoRebootBuildSlave))
    self.assertTrue(isinstance(slaves['S5'], AutoRebootBuildSlave))
    self.assertTrue(isinstance(slaves['S6'], AutoRebootBuildSlave))
    self.assertTrue(isinstance(slaves['S7'], AutoRebootBuildSlave))
    self.assertFalse(isinstance(slaves['S8'], AutoRebootBuildSlave))


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

    def f(builder, slaves):
      # Call original method for code coverage only.
      master_utils.PreferredBuilderNextSlaveFuncNG()(builder, slaves)

      # Mock random.choice on function return for determinism and to check the
      # full choice range.
      mocked_func = master_utils.PreferredBuilderNextSlaveFuncNG(choice=list)
      return set([s.name for s in mocked_func(builder, slaves)])

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
