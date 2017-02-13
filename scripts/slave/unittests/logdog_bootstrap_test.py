#!/usr/bin/env python
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests that the tools/build logdog_bootstrap wrapper actually runs."""

import collections
import json
import logging
import os
import subprocess
import sys
import unittest
import StringIO

import test_env  # pylint: disable=W0403,W0611

import mock
from common import annotator
from common import env
from slave import logdog_bootstrap as ldbs
from slave import cipd
from slave import gce
from slave import infra_platform
from slave import robust_tempdir

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MockOptions = collections.namedtuple('MockOptions',
    ('logdog_butler_path', 'logdog_annotee_path', 'logdog_verbose',
     'logdog_service_account_json', 'logdog_service_host',
     'logdog_viewer_host'))


class LogDogBootstrapTest(unittest.TestCase):

  def setUp(self):
    logging.basicConfig(level=logging.ERROR+1)
    self.maxDiff = None

    self._patchers = []
    map(self._patch, (
        mock.patch('slave.infra_platform.get'),
        mock.patch('slave.logdog_bootstrap._check_call'),
        mock.patch('slave.gce.Authenticator.is_gce'),
        mock.patch('os.environ', {}),
        ))

    self.rt = robust_tempdir.RobustTempdir(prefix='logdog_bootstrap_test')
    self.basedir = self.rt.tempdir()
    self.tdir = self.rt.tempdir()
    self.opts = MockOptions(
        logdog_annotee_path=None,
        logdog_butler_path=None,
        logdog_verbose=False,
        logdog_service_account_json=None,
        logdog_service_host=None,
        logdog_viewer_host=None)
    self.properties = {
      'mastername': 'default',
      'buildername': 'builder',
      'buildnumber': 24601,
    }

    # Stable (default) API.
    self.stable_api = ldbs._CIPD_TAG_API_MAP[ldbs._STABLE_CIPD_TAG]
    self.latest_api = ldbs._CIPD_TAG_API_MAP[ldbs._CANARY_CIPD_TAG]

    # Set of default base params.
    self.base = ldbs.Params(
        project='alpha', cipd_tag=ldbs._STABLE_CIPD_TAG, api=self.stable_api,
        mastername='default', buildername='builder', buildnumber=24601,
        logdog_only=False, cipd_canary=False)

    # Control whether we think we're a GCE instnace.
    gce.Authenticator.is_gce.return_value = False

    # Pretend we're 64-bit Linux by default.
    infra_platform.get.return_value = ('linux', 'x86_64', 64)

  def tearDown(self):
    self.rt.close()
    for p in reversed(self._patchers):
      p.stop()

  def _bp(self, *p):
    return os.path.join(*((self.basedir,) + p))

  def _tp(self, *p):
    return os.path.join(*((self.tdir,) + p))

  def _patch(self, patcher):
    self._patchers.append(patcher)
    patcher.start()
    return patcher

  def _assertAnnoteeCommand(self, value):
    # Double-translate "value", since JSON converts strings to unicode.
    value = json.loads(json.dumps(value))
    with open(self._tp('logdog_annotee_cmd.json')) as fd:
      self.assertEqual(json.load(fd), value)

  @mock.patch('slave.logdog_bootstrap._load_params_dict')
  def test_get_params(self, load_params_dict):
    load_params_dict.return_value = {
      'alpha': {
        'default': {},
        'blacklist': {
          'blacklisted': {'enabled': False},
        },
        'whitelist': {
          'whitelisted': {},
          '*': {'enabled': False},
        },
        'canary': {
          '*': {'cipd_tag': 'canary'},
        },
      },
    }

    base = self.base
    def mp(params):
      props = self.properties.copy()
      props.update({
          'mastername': params.mastername,
          'buildername': params.buildername,
          'buildnumber': params.buildnumber,
      })
      return props


    # No mastername, buildername, and buildnumber returns None.
    with self.assertRaises(ldbs.NotBootstrapped):
        ldbs._get_params(mp(base._replace(mastername=None)))
    with self.assertRaises(ldbs.NotBootstrapped):
        ldbs._get_params(mp(base._replace(buildername=None)))
    with self.assertRaises(ldbs.NotBootstrapped):
        ldbs._get_params(mp(base._replace(buildnumber=None)))

    # Default.
    params = base
    self.assertEqual(ldbs._get_params(mp(params)), params)

    # Blacklist.
    params = base._replace(mastername='blacklist', buildername='blacklisted')
    with self.assertRaises(ldbs.NotBootstrapped):
      ldbs._get_params(mp(params))

    params = base._replace(mastername='blacklist', buildername='other')
    self.assertEqual(ldbs._get_params(mp(params)), params)

    # Whitelist.
    params = base._replace(mastername='whitelist', buildername='whitelisted')
    self.assertEqual(ldbs._get_params(mp(params)), params)

    params = base._replace(mastername='whitelist', buildername='other')
    with self.assertRaises(ldbs.NotBootstrapped):
      ldbs._get_params(mp(params))

    # Canary.
    params = base._replace(mastername='canary', cipd_tag='canary')
    self.assertEqual(ldbs._get_params(mp(params)), params)


  @mock.patch('os.path.isfile')
  @mock.patch('slave.logdog_bootstrap._install_cipd')
  @mock.patch('slave.logdog_bootstrap._get_service_account_json')
  @mock.patch('slave.logdog_bootstrap._get_params')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_bootstrap_command_linux(self, tempdir, get_params, service_account,
                                   install_cipd, isfile):
    butler_path = self._bp('.recipe_logdog_cipd', 'logdog_butler')
    annotee_path = self._bp('.recipe_logdog_cipd', 'logdog_annotee')
    recipe_cmd = ['run_recipe.py', 'recipe_params...']

    tempdir.return_value = 'foo'
    get_params.return_value = ldbs.Params(
        project='myproject', cipd_tag='stable', api=self.stable_api,
        mastername='mastername', buildername='buildername', buildnumber=1337,
        logdog_only=False, cipd_canary=False)
    install_cipd.return_value = (butler_path, annotee_path)
    service_account.return_value = 'creds.json'
    isfile.return_value = True

    streamserver_uri = 'unix:%s' % (os.path.join('foo', 'butler.sock'),)

    bs = ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                        self.properties, recipe_cmd)
    self.assertEqual(
        bs.cmd,
        [butler_path,
            '-log-level', 'warning',
            '-project', 'myproject',
            '-prefix', 'bb/mastername/buildername/1337',
            '-output', 'logdog,host="services-dot-luci-logdog.appspot.com"',
            '-coordinator-host', 'luci-logdog.appspot.com',
            '-tag', 'buildbot.master=mastername',
            '-tag', 'buildbot.builder=buildername',
            '-tag', 'buildbot.buildnumber=1337',
            '-service-account-json', 'creds.json',
            '-output-max-buffer-age', '30s',
            'run',
            '-stdout', 'tee=stdout',
            '-stderr', 'tee=stderr',
            '-streamserver-uri', streamserver_uri,
            '--',
            annotee_path,
                '-log-level', 'warning',
                '-project', 'myproject',
                '-butler-stream-server', streamserver_uri,
                '-logdog-host', 'luci-logdog.appspot.com',
                '-name-base', 'recipes',
                '-print-summary',
                '-tee', 'annotations,text',
                '-json-args-path', self._tp('logdog_annotee_cmd.json'),
                '-result-path', self._tp('bootstrap_result.json'),
        ])

    service_account.assert_called_once_with(
        self.opts, ldbs._PLATFORM_CONFIG[('linux',)]['credential_path'])
    self._assertAnnoteeCommand(recipe_cmd)

  @mock.patch('os.path.isfile')
  @mock.patch('slave.logdog_bootstrap._install_cipd')
  @mock.patch('slave.logdog_bootstrap._get_service_account_json')
  @mock.patch('slave.logdog_bootstrap._get_params')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_bootstrap_command_windows(self, tempdir, get_params, service_account,
                                     install_cipd, isfile):
    infra_platform.get.return_value = ('win', 'x86_64', 64)

    recipe_cmd = ['run_recipe.py', 'recipe_params...']

    tempdir.return_value = 'foo'
    get_params.return_value = ldbs.Params(
        project='myproject', cipd_tag='stable',
        api=self.latest_api, mastername='mastername',
        buildername='buildername', buildnumber=1337, logdog_only=True,
        cipd_canary=True)
    install_cipd.return_value = ('logdog_butler.exe', 'logdog_annotee.exe')
    service_account.return_value = 'creds.json'
    isfile.return_value = True

    streamserver_uri = 'net.pipe:LUCILogDogButler'

    bs = ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                        self.properties, recipe_cmd)
    self.assertEqual(
        bs.cmd,
        ['logdog_butler.exe',
            '-log-level', 'warning',
            '-project', 'myproject',
            '-prefix', 'bb/mastername/buildername/1337',
            '-output', 'logdog,host="services-dot-luci-logdog.appspot.com"',
            '-coordinator-host', 'luci-logdog.appspot.com',
            '-tag', 'buildbot.master=mastername',
            '-tag', 'buildbot.builder=buildername',
            '-tag', 'buildbot.buildnumber=1337',
            '-service-account-json', 'creds.json',
            '-output-max-buffer-age', '30s',
            '-io-keepalive-stderr', '5m',
            'run',
            '-stdout', 'tee=stdout',
            '-stderr', 'tee=stderr',
            '-streamserver-uri', streamserver_uri,
            '--',
            'logdog_annotee.exe',
                '-log-level', 'warning',
                '-project', 'myproject',
                '-butler-stream-server', streamserver_uri,
                '-logdog-host', 'luci-logdog.appspot.com',
                '-name-base', 'recipes',
                '-print-summary',
                '-tee', 'annotations',
                '-json-args-path', self._tp('logdog_annotee_cmd.json'),
                '-result-path', self._tp('bootstrap_result.json'),
        ])

    service_account.assert_called_once_with(
        self.opts, ldbs._PLATFORM_CONFIG[('win',)]['credential_path'])
    self._assertAnnoteeCommand(recipe_cmd)

  @mock.patch('os.path.isfile')
  @mock.patch('slave.logdog_bootstrap._install_cipd')
  @mock.patch('slave.logdog_bootstrap._get_service_account_json')
  @mock.patch('slave.logdog_bootstrap._get_params')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_registered_apis_work(self, tempdir, get_params, service_account,
                                install_cipd, isfile):
    tempdir.return_value = 'foo'
    isfile.return_value = True
    butler_path = self._bp('.recipe_logdog_cipd', 'logdog_butler')
    annotee_path = self._bp('.recipe_logdog_cipd', 'logdog_annotee')
    service_account.return_value = 'creds.json'

    install_cipd.return_value = (butler_path, annotee_path)

    for api in sorted(ldbs._CIPD_TAG_API_MAP.values()):
      get_params.return_value = self.base._replace(api=api)
      ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                     self.properties, [])

  def test_get_bootstrap_result(self):
    mo = mock.mock_open(read_data='{"return_code": 1337}')
    with mock.patch('slave.logdog_bootstrap.open', mo, create=True):
      bs = ldbs.BootstrapState([], '/foo/bar', 'project', 'prefix')
      self.assertEqual(bs.get_result(), 1337)

    mo = mock.mock_open(read_data='!!! NOT JSON? !!!')
    with mock.patch('slave.logdog_bootstrap.open', mo, create=True):
      bs = ldbs.BootstrapState([], '/foo/bar', 'project', 'prefix')
      self.assertRaises(ldbs.BootstrapError, bs.get_result)

    mo = mock.mock_open(read_data='{"invalid": "json"}')
    with mock.patch('slave.logdog_bootstrap.open', mo, create=True):
      bs = ldbs.BootstrapState([], '/foo/bar', 'project', 'prefix')
      self.assertRaises(ldbs.BootstrapError, bs.get_result)

    mo = mock.mock_open()
    with mock.patch('slave.logdog_bootstrap.open', mo, create=True):
      mo.side_effect = IOError('Test not found')
      self.assertRaises(ldbs.BootstrapError, bs.get_result)

  def test_bootstrap_annotations(self):
    sio = StringIO.StringIO()
    stream = annotator.StructuredAnnotationStream(stream=sio)
    bs = ldbs.BootstrapState([], '/foo/bar', 'project', 'foo/bar/baz')
    bs.annotate(stream)

    lines = [l for l in sio.getvalue().splitlines() if l]
    self.assertEqual(lines, [
        '@@@SEED_STEP LogDog Bootstrap@@@',
        '@@@STEP_CURSOR LogDog Bootstrap@@@',
        '@@@STEP_STARTED@@@',
        '@@@SET_BUILD_PROPERTY@logdog_project@"project"@@@',
        '@@@SET_BUILD_PROPERTY@logdog_prefix@"foo/bar/baz"@@@',
        '@@@STEP_CURSOR LogDog Bootstrap@@@',
        '@@@STEP_CLOSED@@@',
    ])

  @mock.patch('os.path.isfile')
  def test_can_find_credentials(self, isfile):
    isfile.return_value = True

    service_account_json = ldbs._get_service_account_json(
        self.opts, 'creds.json')
    self.assertEqual(service_account_json, 'creds.json')

  def test_uses_no_credentials_on_gce(self):
    gce.Authenticator.is_gce.return_value = True

    service_account_json = ldbs._get_service_account_json(
        self.opts, ('foo', 'bar'))
    self.assertIsNone(service_account_json)

  def test_cipd_install(self):
    pkgs = ldbs._install_cipd(self.basedir, False,
        cipd.CipdBinary(cipd.CipdPackage('infra/foo', 'v0'), 'foo'),
        cipd.CipdBinary(cipd.CipdPackage('infra/bar', 'v1'), 'baz'),
        )
    self.assertEqual(pkgs, (self._bp('foo'), self._bp('baz')))

    ldbs._check_call.assert_called_once_with([
      sys.executable,
       os.path.join(env.Build, 'scripts', 'slave', 'cipd.py'),
       '--dest-directory', self.basedir,
       '-P', 'infra/foo@v0',
       '-P', 'infra/bar@v1',
    ])

  def test_cipd_install_canary(self):
    pkgs = ldbs._install_cipd(self.basedir, True,
        cipd.CipdBinary(cipd.CipdPackage('infra/foo', 'v0'), 'foo'),
        cipd.CipdBinary(cipd.CipdPackage('infra/bar', 'v1'), 'baz'),
        )
    self.assertEqual(pkgs, (self._bp('foo'), self._bp('baz')))

    ldbs._check_call.assert_called_once_with([
      sys.executable,
       os.path.join(env.Build, 'scripts', 'slave', 'cipd.py'),
       '--dest-directory', self.basedir,
       '--canary',
       '-P', 'infra/foo@v0',
       '-P', 'infra/bar@v1',
    ])

  def test_cipd_install_failure_raises_bootstrap_error(self):
    ldbs._check_call.side_effect = subprocess.CalledProcessError(0, [], '')

    self.assertRaises(ldbs.BootstrapError,
        ldbs._install_cipd,
        self.basedir,
        cipd.CipdBinary(cipd.CipdPackage('infra/foo', 'v0'), 'foo'),
        cipd.CipdBinary(cipd.CipdPackage('infra/bar', 'v1'), 'baz'),
    )

  def test_will_not_bootstrap_if_recursive(self):
    os.environ['LOGDOG_STREAM_PREFIX'] = 'foo'
    with self.assertRaises(ldbs.NotBootstrapped):
      ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                    self.properties, [])


class TestPublicParams(unittest.TestCase):

  def setUp(self):
    logging.basicConfig(level=logging.DEBUG)

  def test_load(self):
    params = ldbs._load_params_dict('chromium')
    self.assertIsInstance(params, dict)

    # Get a list of all defined master/builders, plus a "TESTING" builder to
    # test '*' defaults.
    combos = set()
    for _, masters in params.iteritems():
      for master, builders in masters.iteritems():
        for builder in builders.iterkeys():
          combos.add((master, builder))
        combos.add((master, 'TESTING'))

    for master, builder in sorted(combos):
      params = ldbs._get_params({
          'mastername': master,
          'buildername': builder,
          'buildnumber': 24601,
      })
      self.assertIsInstance(params, ldbs.Params)


if __name__ == '__main__':
  unittest.main()
