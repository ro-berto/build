#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for scripts/tools/mastermap.py"""


import unittest

import test_env  # pylint: disable=W0611

from tools import mastermap


class FakeOutput(object):
  def __init__(self):
    self.lines = None

  def __call__(self, lines, _verbose):
    self.lines = lines


class FakeOpts(object):
  verbose = None


class HelperTest(unittest.TestCase):

  def test_getint_succeeds(self):
    res = mastermap.getint('10')
    self.assertEquals(res, 10)

  def test_getint_fails(self):
    res = mastermap.getint('foo')
    self.assertEquals(res, 0)

  def test_format_host_name_chromium(self):
    res = mastermap.format_host_name('master1.golo.chromium.org')
    self.assertEquals(res, 'master1.golo')

  def test_format_host_name_corp(self):
    res = mastermap.format_host_name('master.chrome.corp.google.com')
    self.assertEquals(res, 'master.chrome')

  def test_format_host_name_neither(self):
    res = mastermap.format_host_name('mymachine.tld')
    self.assertEquals(res, 'mymachine.tld')


class MapTest(unittest.TestCase):

  def test_column_names(self):
    output = FakeOutput()
    mastermap.master_map([], output, FakeOpts())
    self.assertEqual(len(output.lines), 1)
    self.assertEqual(
        output.lines,
        [['Master', 'Config Dir', 'Host', 'Web port', 'Slave port',
          'Alt port', 'URL']])

  def test_same_number_of_columns(self):
    output = FakeOutput()
    master = {
      'name': 'Chromium',
      'dirname': 'master.chromium',
      'host': 'master1.golo',
      'port': 30101,
      'slave_port': 40101,
      'alt_port': 50101,
      'buildbot_url': 'https://build.chromium.org/p/chromium',
    }
    mastermap.master_map([master], output, FakeOpts())
    self.assertEqual(len(output.lines), 2)
    self.assertEqual(len(output.lines[0]), len(output.lines[1]))


class FindPortTest(unittest.TestCase):

  @staticmethod
  def _gen_masters(num):
    return [{
        'name': 'Master%d' % i,
        'dirname': 'master.master%d' % i,
        'host': 'master1.golo',
        'port': 30100 + i,
        'slave_port': 40100 + i,
        'alt_port': 50100 + i,
    } for i in xrange(num)]

  def test_master_not_found(self):
    masters = self._gen_masters(1)
    mastername = 'MasterFoo'
    output = FakeOutput()
    res = mastermap.find_port(mastername, masters, output, FakeOpts())
    self.assertTrue('not found' in output.lines[0][0])
    self.assertEquals(res, 1)

  def test_skip_used_ports(self):
    masters = self._gen_masters(5)
    masters.append({'name': 'Master6', 'host': 'master1.golo'})
    mastername = 'Master6'
    output = FakeOutput()
    res = mastermap.find_port(mastername, masters, output, FakeOpts())
    self.assertEquals(res, None)
    self.assertEquals(len(output.lines), 2)
    self.assertEquals(output.lines[1][0], '30105')
    self.assertEquals(output.lines[1][1], '40105')
    self.assertEquals(output.lines[1][2], '50105')

  def test_skip_blacklisted_ports(self):
    masters = [{'name': 'Master1', 'host': 'master1.golo'}]
    mastername = 'Master1'
    output = FakeOutput()
    _real_blacklist = mastermap.PORT_BLACKLIST
    try:
      mastermap.PORT_BLACKLIST = set(range(50000, 60000))  # All alt_ports
      res = mastermap.find_port(mastername, masters, output, FakeOpts())
      print output.lines
      self.assertTrue('unable to find' in output.lines[0][0])
      self.assertEquals(res, 1)
    finally:
      mastermap.PORT_BLACKLIST = _real_blacklist


class AuditTest(unittest.TestCase):
  # TODO(agable): Actually test this.
  pass


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()
