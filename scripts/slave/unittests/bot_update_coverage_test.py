#!/usr/bin/env vpython
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import codecs
import copy
import json
import os
import sys
import unittest

import test_env  # pylint: disable=relative-import

sys.platform = 'linux2'  # For consistency, ya know?
from slave import bot_update

DEFAULT_PARAMS = {
    'solutions': [{
        'name': 'somename',
        'url': 'https://fake.com'
    }],
    'revisions': [],
    'first_sln': 'somename',
    'target_os': None,
    'target_os_only': None,
    'patch_root': None,
    'issue': None,
    'patchset': None,
    'patch_url': None,
    'rietveld_server': None,
    'gerrit_ref': None,
    'gerrit_repo': None,
    'revision_mapping': {},
    'apply_issue_email_file': None,
    'apply_issue_key_file': None,
    'buildspec': False,
    'gyp_env': None,
    'shallow': False,
    'runhooks': False,
    'refs': [],
}


class MockedPopen(object):
  """A fake instance of a called subprocess.

  This is meant to be used in conjunction with MockedCall.
  """
  def __init__(self, args=None, kwargs=None):
    self.args = args or []
    self.kwargs = kwargs or {}
    self.return_value = None
    self.fails = False

  def returns(self, rv):
    """Set the return value when this popen is called.

    rv can be a string, or a callable (eg function).
    """
    self.return_value = rv
    return self

  def check(self, args, kwargs):
    """Check to see if the given args/kwargs call match this instance.

    This does a partial match, so that a call to "git clone foo" will match
    this instance if this instance was recorded as "git clone"
    """
    if any(input_arg != expected_arg
           for (input_arg, expected_arg) in zip(args, self.args)):
      return False
    return self.return_value

  def __call__(self, args, kwargs):
    """Actually call this popen instance."""
    if hasattr(self.return_value, '__call__'):
      return self.return_value(*args, **kwargs)
    return self.return_value


class MockedCall(object):
  """A fake instance of bot_update.call().

  This object is pre-seeded with "answers" in self.expectations.  The type
  is a MockedPopen object, or any object with a __call__() and check() method.
  The check() method is used to check to see if the correct popen object is
  chosen (can be a partial match, eg a "git clone" popen module would match
  a "git clone foo" call).
  By default, if no answers have been pre-seeded, the call() returns successful
  with an empty string.
  """
  def __init__(self, fake_filesystem):
    self.expectations = []
    self.records = []

  def expect(self, args=None, kwargs=None):
    args = args or []
    kwargs = kwargs or {}
    popen = MockedPopen(args, kwargs)
    self.expectations.append(popen)
    return popen

  def __call__(self, *args, **kwargs):
    self.records.append((args, kwargs))
    for popen in self.expectations:
      if popen.check(args, kwargs):
        self.expectations.remove(popen)
        return popen(args, kwargs)
    return ''


class MockedGclientSync():
  """A class producing a callable instance of gclient sync.

  Because for bot_update, gclient sync also emits an output json file, we need
  a callable object that can understand where the output json file is going, and
  emit a (albite) fake file for bot_update to consume.
  """
  def __init__(self, fake_filesystem):
    self.output = {}
    self.fake_filesystem = fake_filesystem

  def __call__(self, *args, **_):
    output_json_index = args.index('--output-json') + 1
    with self.fake_filesystem.open(args[output_json_index], 'w') as f:
      json.dump(self.output, f)


class FakeFile():
  def __init__(self):
    self.contents = ''

  def write(self, buf):
    self.contents += buf

  def read(self):
    return self.contents

  def __enter__(self):
    return self

  def __exit__(self, _, __, ___):
    pass


class FakeFilesystem():
  def __init__(self):
    self.files = {}

  def open(self, target, mode='r', encoding=None):
    if 'w' in mode:
      self.files[target] = FakeFile()
      return self.files[target]
    return self.files[target]


def fake_git(*args, **kwargs):
  return bot_update.call('git', *args, **kwargs)


class BotUpdateUnittests(unittest.TestCase):
  def setUp(self):
    self.filesystem = FakeFilesystem()
    self.call = MockedCall(self.filesystem)
    self.gclient = MockedGclientSync(self.filesystem)
    self.call.expect(('gclient', 'sync')).returns(self.gclient)
    self.old_call = getattr(bot_update, 'call')
    self.params = copy.deepcopy(DEFAULT_PARAMS)
    setattr(bot_update, 'call', self.call)
    setattr(bot_update, 'git', fake_git)

    self.old_os_cwd = os.getcwd
    setattr(os, 'getcwd', lambda: '/b/build/slave/foo/build')

    setattr(bot_update, 'open', self.filesystem.open)
    self.old_codecs_open = codecs.open
    setattr(codecs, 'open', self.filesystem.open)

  def tearDown(self):
    setattr(bot_update, 'call', self.old_call)
    setattr(os, 'getcwd', self.old_os_cwd)
    delattr(bot_update, 'open')
    setattr(codecs, 'open', self.old_codecs_open)

  def testBasic(self):
    bot_update.ensure_checkout(**self.params)
    return self.call.records

  def testBasicBuildspec(self):
    self.params['buildspec'] = bot_update.BUILDSPEC_TYPE(
        container='branches',
        version='1.1.1.1'
    )
    bot_update.ensure_checkout(**self.params)
    return self.call.records

  def testBasicShallow(self):
    self.params['shallow'] = True
    bot_update.ensure_checkout(**self.params)
    return self.call.records


if __name__ == '__main__':
  unittest.main()
