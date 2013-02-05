#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import tempfile
import time
import unittest
import webbrowser

import test_env

import mock

from buildbot.status import results
from buildbot.status.builder import BuildStatus, BuildStepStatus
from buildbot.status.logfile import LogFile
from buildbot.status.master  import Status as MasterStatus

from master.build_utils import FakeBuild
from master.try_mail_notifier import TryMailNotifier


class TestMailNotifier(unittest.TestCase):
  TEST_MODE = 0
  TRAIN_MODE = 1
  mode = TEST_MODE

  def __init__(self, *args, **kwargs):
    super(TestMailNotifier, self).__init__(*args, **kwargs)
    self.maxDiff = None
    os.environ['TZ'] = 'PST+08'
    time.tzset()

  @mock.patch('time.time')  # Needed to fix time while generating the email
  def check_mail(
      self, bs_cfg, step_cfgs, log_cfgs, ms_cfg, expected, test_name, _
    ):
    '''
    bs_cfg: BuildStatus config dict
    step_cfgs: [BuildStepStatus config dict]
    log_cfgs: [[LogFile config dict]]
    ms_cfg: MasterStatus config dict
    '''
    mn = TryMailNotifier(
        fromaddr='from@example.org',
        subject="try %(result)s for %(reason)s on %(builder)s @ r%(revision)s",
        mode="all")

    bs = mock.Mock(BuildStatus)

    steps = []
    for step_cfg, logs_cfg in zip(step_cfgs, log_cfgs):
      step = mock.Mock(BuildStepStatus)
      logs = []
      for l_cfg in logs_cfg:
        log = mock.Mock(LogFile)
        log.configure_mock(**l_cfg)
        logs.append(log)
      step.urls = {}
      step_cfg.update({
        'getLogs.return_value': logs,
        'addURL.side_effect': lambda name, url: step.urls.update({name: url}),
        'getURLs.side_effect': step.urls.copy,
        'getBuild.return_value': bs,
      })
      step.configure_mock(**step_cfg)
      steps.append(step)

    bs_cfg.update({'getSteps.return_value': steps})
    bs.configure_mock(**bs_cfg)

    def assertBuildStatus(build):
      assert isinstance(build, BuildStatus)

    ms = mock.Mock(MasterStatus)
    ms_cfg.update({'getURLForThing.side_effect': assertBuildStatus})
    ms.configure_mock(**ms_cfg)

    mn.master_status = ms

    mail = mn.buildMessage_internal('FakeBuilder', [bs], bs.getResults())
    # Set the boundary. Otherwise it's randomly generated and breaks the
    # test cases.
    mail.set_boundary('===============7454617213454723890==')

    mail_str = str(mail)
    if self.mode == self.TEST_MODE:
      with open(expected, 'rb') as expected_file:
        self.assertEqual(mail_str, expected_file.read())
    elif self.mode == self.TRAIN_MODE:
      with tempfile.NamedTemporaryFile(suffix='.html') as f:
        f.write(mail.get_payload(0).get_payload(decode=True))
        f.flush()
        webbrowser.open('file://%s' % f.name)
        answer = raw_input(
          'Accept as new test data for %s [y/N]? ' % test_name).strip().lower()
      if answer == 'y':
        with open(expected, 'wb') as expected_file:
          expected_file.write(mail_str)


def recursive_key_replace(obj, find, replace):
  """Recursively transforms the keys of a json-like object.

  In particular, it will leave non-key values alone and will traverse any
  number of dictionaries/lists to completely transform obj.

  Example:
    INPUT:
      { 'test_': [['not_transformed', {'tweak_this': 100}]] }
    OUTPUT (find='_', replace='-'):
      { 'test-': [['not_transformed', {'tweak-this': 100}]] }
  """
  if isinstance(obj, dict):
    ret = {}
    for k, v in obj.iteritems():
      k = k.replace(find, replace)
      if isinstance(v, (list, dict)):
        v = recursive_key_replace(v, find, replace)
      ret[k] = v
  elif isinstance(obj, list):
    ret = []
    for v in obj:
      if isinstance(v, (list, dict)):
        v = recursive_key_replace(v, find, replace)
      ret.append(v)
  else:
    assert False, 'obj must be a list or dict'
  return ret


def test_from_files(infile, expected, name):
  env = {'results': results}
  def inner(self):
    with open(infile) as f:
      data = eval(f.read(), {}, env)
    data['build_step']['getProperties()'] = FakeBuild(data['build_step_props'])
    data = recursive_key_replace(data, '()', '.return_value')
    self.check_mail(
        data['build_step'], data['steps'], data['logs'], data['master'],
        expected, name
    )
  return inner


def addTests():
  base_path = os.path.join(test_env.DATA_PATH, 'trymail_tests')
  for fname in os.listdir(base_path):
    if fname.endswith('.in'):
      path = os.path.join(base_path, fname)
      name = os.path.splitext(fname)[0]
      expected = os.path.join(base_path, name+'.expected')
      setattr(
          TestMailNotifier, 'test_%s' % name,
          test_from_files(path, expected, name)
      )
addTests()


def main(argv):
  if '--help' in argv or '-h' in argv:
    print 'Pass --train to enter training mode.'
    print
  elif '--train' in argv:
    argv.remove('--train')
    TestMailNotifier.mode = TestMailNotifier.TRAIN_MODE

  unittest.main()


if __name__ == '__main__':
  sys.exit(main(sys.argv))

# vim: set ts=2 sts=2 sw=2:
