#!/usr/bin/env vpython
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for floating builder testcases."""

import calendar
import datetime
import itertools
import os
import time
import unittest

import mock

import test_env  # pylint: disable=relative-import

from master import floating_builder as fb


def _to_timestamp(dt):
  # Calculate the offset between local timezone and UTC.
  current_time = time.mktime(dt.timetuple())
  offset = (datetime.datetime.fromtimestamp(current_time) -
            datetime.datetime.utcfromtimestamp(current_time))

  return calendar.timegm((dt - offset).timetuple())


class _FakeSlaveStatus(object):
  def __init__(self, name):
    self.name = name
    self.connect_times = []
    self.last_message_received = None

  def lastMessageReceived(self):
    return self.last_message_received


class _FakeSlave(object):
  def __init__(self, slavename):
    self.slavename = slavename
    self.slave_status = None
    self.offline = False

  def _set_last_seen(self, now, **kwargs):
    td = datetime.timedelta(**kwargs)
    self.slave_status = _FakeSlaveStatus(self.slavename)
    self.slave_status.last_message_received = _to_timestamp(now + td)

  def __str__(self):
    return self.slavename


class _FakeBuilder(object):

  def __init__(self, name, slaves):
    self.name = name
    self._all_slaves = slaves

    self.botmaster = mock.MagicMock()
    self.builder_status = mock.MagicMock()
    self.builder_status.getSlaves.side_effect = lambda: [
        s.slave_status for s in self._all_slaves
        if s.slave_status]

    self._online_slaves = ()
    self._busy_slaves = ()

  def __repr__(self):
    return self.name

  @property
  def slaves(self):
    return [_FakeSlaveBuilder(s, self)
            for s in self._all_slaves
            if s.slavename in self._online_slaves]

  @property
  def slavebuilders(self):
    """Returns the list of slavebuilders that would be handed to
    NextSlaveFunc.

    This is the set of slaves that are available for scheduling. We derive
    this by returning all slaves that are both online and not busy.
    """
    return self._get_slave_builders(lambda s:
      s.slavename in self._online_slaves and
      s.slavename not in self._busy_slaves)

  def _get_slave_builders(self, fn):
    return [_FakeSlaveBuilder(slave, self)
            for slave in self._all_slaves
            if fn(slave)]

  def set_online_slaves(self, *slavenames):
    self._online_slaves = set(slavenames)

  def set_busy_slaves(self, *slavenames):
    self._busy_slaves = set(slavenames)


class _FakeSlaveBuilder(object):

  def __init__(self, slave, builder):
    self.slave = slave
    self.builder = builder

  def __repr__(self):
    return '{%s/%s}' % (self.builder.name, self.slave.slavename)


class FloatingBuilderTest(unittest.TestCase):

  def setUp(self):
    self._mocks = (
      mock.patch('master.floating_builder._get_now'),
      mock.patch('master.floating_builder.PokeBuilderTimer.reset'),
    )
    for patcher in self._mocks:
      patcher.start()

    # Mock current date/time.
    self.now = datetime.datetime(2016, 1, 1, 8, 0, 0) # 1/1/2016 @8:00
    fb._get_now.side_effect = lambda: self.now

    # Mock PokeBuilderTimer to record when the poke builder was set, but not
    # actually schedule any reactor magic.
    self.poke_delta = None
    def record_poke_delta(delta):
      self.poke_delta = delta
    fb.PokeBuilderTimer.reset.side_effect = record_poke_delta

    self._slaves = dict((s, _FakeSlave(s)) for s in (
        'primary-a', 'primary-b', 'floating-a', 'floating-b',
    ))

    self.builder = _FakeBuilder(
        'Test Builder',
        [s[1] for s in sorted(self._slaves.iteritems())],
    )

  def tearDown(self):
    for patcher in reversed(self._mocks):
      patcher.stop()

  def testJustStartedNoPrimariesOnlineWaits(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSlaveFunc(datetime.timedelta(seconds=10))

    self.builder.set_online_slaves('floating-a', 'floating-b')

    nsb = fnsf(self.builder, self.builder.slavebuilders)
    self.assertIsNone(nsb)
    self.assertEqual(self.poke_delta, datetime.timedelta(seconds=10))

    self.now += datetime.timedelta(seconds=11)
    nsb = fnsf(self.builder, self.builder.slavebuilders)
    self.assertIsNotNone(nsb)
    self.assertEqual(nsb.slave.slavename, 'floating-a')

  def testPrimaryBuilderIsSelectedWhenAvailable(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSlaveFunc(datetime.timedelta(seconds=10))

    self.builder.set_online_slaves('primary-a', 'floating-a', 'floating-b')

    nsb = fnsf(self.builder, self.builder.slavebuilders)
    self.assertIsNotNone(nsb)
    self.assertEqual(nsb.slave.slavename, 'primary-a')

  def testPrimaryBuilderIsSelectedWhenOneIsAvailableAndOneIsBusy(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a', 'primary-b')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSlaveFunc(datetime.timedelta(seconds=10))

    self.builder.set_online_slaves('primary-a', 'primary-b', 'floating-a',
                                   'floating-b')
    self.builder.set_busy_slaves('primary-a')

    nsb = fnsf(self.builder, self.builder.slavebuilders)
    self.assertIsNotNone(nsb)
    self.assertEqual(nsb.slave.slavename, 'primary-b')

  def testNoBuilderIsSelectedWhenPrimariesAreOfflineWithinGrace(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a', 'primary-b')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSlaveFunc(datetime.timedelta(seconds=10))

    self.now += datetime.timedelta(seconds=30)
    self.builder.set_online_slaves('floating-a')
    self._slaves['primary-b']._set_last_seen(self.now, seconds=-1)

    nsb = fnsf(self.builder, self.builder.slavebuilders)
    self.assertIsNone(nsb)
    self.assertEqual(self.poke_delta, datetime.timedelta(seconds=9))

  def testFloatingBuilderIsSelectedWhenPrimariesAreOfflineForAWhile(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a', 'primary-b')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSlaveFunc(datetime.timedelta(seconds=10))

    self.now += datetime.timedelta(seconds=30)
    self.builder.set_online_slaves('floating-a')

    nsb = fnsf(self.builder, self.builder.slavebuilders)
    self.assertIsNotNone(nsb)
    self.assertEqual(nsb.slave.slavename, 'floating-a')


if __name__ == '__main__':
  unittest.main()
