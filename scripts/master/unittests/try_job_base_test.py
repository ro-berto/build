#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""try_job_base.py testcases."""

import unittest

import test_env  # pylint: disable=W0611

from master import try_job_base


class PaseOptionsTest(unittest.TestCase):
  @staticmethod
  def _get_default():
    return {
        'bot': {},
        'branch': None,
        'email': [],
        'issue': None,
        'name': 'Unnamed',
        'patch': None,
        'patchlevel': 0,
        'patchset': None,
        'project': None,
        'reason': 'John Doe: Unnamed',
        'repository': None,
        'revision': None,
        'root': None,
        'testfilter': [],
        'user': 'John Doe',
    }

  def test_parse_options_defaults(self):
    expected = self._get_default()
    expected.update({'bot': {'bot1': []}})
    self.assertEquals(
        expected,
        try_job_base.parse_options({'bot': ['bot1']}, None))

  def test_dict_comma1(self):
    values = [
      # The currently supported formats are a bit messy while we transition
      # to something sane.
      'bot1:test1,bot2',
      'bot1:test2:foo.*',
      'bot3,bot4',
    ]
    expected = {
      'bot1': ['test1', 'test2:foo.*'],
      'bot2': [],
      'bot3': [],
      'bot4': [],
    }
    self.assertEquals(expected, try_job_base.dict_comma(values))

  def test_dict_comma2(self):
    values = [
      ('linux_chromeos,win_rel,linux_chromeos_aura:compile,linux_view,'
       'mac_rel,linux_rel'),
    ]
    expected = {
      'linux_chromeos': [],
      'linux_chromeos_aura': ['compile'],
      'linux_rel': [],
      'linux_view': [],
      'mac_rel': [],
      'win_rel': [],
    }
    self.assertEquals(expected, try_job_base.dict_comma(values))

  def testParseText(self):
    text = (
        'foo=bar\n'
        '\n'
        'Ignored text\n'
        'ignored_key=\n'
        '=ignored_value\n'
        'DUPE=dupe1\n'
        'DUPE=dupe2\n')
    expected = {
        'foo': ['bar'],
        'DUPE': ['dupe1', 'dupe2'],
    }
    self.assertEquals(expected, try_job_base.text_to_dict(text))


if __name__ == '__main__':
  unittest.main()
