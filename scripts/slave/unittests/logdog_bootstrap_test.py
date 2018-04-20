#!/usr/bin/env vpython
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

import mock

import test_env  # pylint: disable=relative-import

from common import annotator
from common import env
from slave import logdog_bootstrap as ldbs
from slave import cipd
from slave import cipd_bootstrap_v2
from slave import gce
from slave import infra_platform
from slave import robust_tempdir

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MockOptions = collections.namedtuple('MockOptions', (
    'logdog_verbose', 'logdog_disable', 'logdog_butler_path',
    'logdog_annotee_path', 'logdog_service_account_json', 'logdog_host',
    'logdog_debug_out_file'))


class LogDogBootstrapTest(unittest.TestCase):

  def setUp(self):
    logging.basicConfig(level=logging.ERROR+1)
    self.maxDiff = None

    self._patchers = []
    map(self._patch, (
        mock.patch('slave.infra_platform.get'),
        mock.patch('slave.logdog_bootstrap._check_call'),
        mock.patch('slave.gce.Authenticator.is_gce'),
        mock.patch('slave.cipd_bootstrap_v2.install_cipd_packages'),
        mock.patch('os.environ', {}),
        ))

    self.rt = robust_tempdir.RobustTempdir(prefix='logdog_bootstrap_test')
    self.basedir = self.rt.tempdir()
    self.tdir = self.rt.tempdir()
    self.opts = MockOptions(
        logdog_verbose=False,
        logdog_disable=False,
        logdog_butler_path=None,
        logdog_annotee_path=None,
        logdog_service_account_json=None,
        logdog_host=None,
        logdog_debug_out_file=None)
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
        generation=None)

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
  @mock.patch('slave.logdog_bootstrap._get_params')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_bootstrap_command_linux_stable(self, tempdir, get_params, isfile):
    gce.Authenticator.is_gce.return_value = True
    recipe_cmd = ['recipes.py', 'recipe_params...']

    tempdir.return_value = 'foo'
    get_params.return_value = ldbs.Params(
        project='myproject', cipd_tag='stable', api=self.stable_api,
        mastername='mastername', buildername='buildername', buildnumber=1337,
        generation=None)
    isfile.return_value = True

    streamserver_uri = 'unix:%s' % (os.path.join('foo', 'butler.sock'),)

    bs = ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                        self.properties, recipe_cmd)

    # Check CIPD installation.
    cipd_dir = os.path.join(self.basedir, '.recipe_cipd')
    cipd_bootstrap_v2.install_cipd_packages.assert_called_once_with(
        cipd_dir,
        cipd.CipdPackage(
            name='infra/tools/luci/logdog/butler/${platform}',
            version='stable'),
        cipd.CipdPackage(
            name='infra/tools/luci/logdog/annotee/${platform}',
            version='stable'),
    )

    # Check bootstrap command.
    self.assertEqual(
        bs.cmd,
        [os.path.join(cipd_dir, 'logdog_butler'),
            '-log-level', 'warning',
            '-project', 'myproject',
            '-prefix', 'bb/mastername/buildername/1337',
            '-coordinator-host', 'logs.chromium.org',
            '-output', 'logdog',
            '-tag', 'buildbot.master=mastername',
            '-tag', 'buildbot.builder=buildername',
            '-tag', 'buildbot.buildnumber=1337',
            '-tag', 'logdog.viewer_url=https://luci-milo.appspot.com/buildbot/'
                    'mastername/buildername/1337',
            '-service-account-json', ':gce',
            '-output-max-buffer-age', '30s',
            '-io-keepalive-stderr', '5m',
            'run',
            '-stdout', 'tee=stdout',
            '-stderr', 'tee=stderr',
            '-streamserver-uri', streamserver_uri,
            '--',
            os.path.join(cipd_dir, 'logdog_annotee'),
                '-log-level', 'warning',
                '-name-base', 'recipes',
                '-print-summary',
                '-tee', 'annotations',
                '-json-args-path', self._tp('logdog_annotee_cmd.json'),
                '-result-path', self._tp('bootstrap_result.json'),
        ])

    self._assertAnnoteeCommand(recipe_cmd)

  @mock.patch('os.path.isfile')
  @mock.patch('slave.logdog_bootstrap._get_service_account_json')
  @mock.patch('slave.logdog_bootstrap._get_params')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_bootstrap_command_win_stable(self, tempdir, get_params,
                                        service_account, isfile):
    infra_platform.get.return_value = ('win', 'x86_64', 64)

    recipe_cmd = ['recipes.py', 'recipe_params...']

    tempdir.return_value = 'foo'
    get_params.return_value = ldbs.Params(
        project='myproject', cipd_tag='stable',
        api=self.stable_api, mastername='mastername',
        buildername='buildername', buildnumber=1337, generation='1')
    service_account.return_value = 'creds.json'
    isfile.return_value = True

    streamserver_uri = 'net.pipe:LUCILogDogButler'

    bs = ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                        self.properties, recipe_cmd)

    # Check CIPD installation.
    cipd_dir = os.path.join(self.basedir, '.recipe_cipd')
    cipd_bootstrap_v2.install_cipd_packages.assert_called_once_with(
        cipd_dir,
        cipd.CipdPackage(
            name='infra/tools/luci/logdog/butler/${platform}',
            version='stable'),
        cipd.CipdPackage(
            name='infra/tools/luci/logdog/annotee/${platform}',
            version='stable'),
    )

    # Check bootstrap command.
    self.assertEqual(
        bs.cmd,
        [os.path.join(cipd_dir, 'logdog_butler.exe'),
            '-log-level', 'warning',
            '-project', 'myproject',
            '-prefix', 'bb/mastername/buildername/1/1337',
            '-coordinator-host', 'logs.chromium.org',
            '-output', 'logdog',
            '-tag', 'buildbot.master=mastername',
            '-tag', 'buildbot.builder=buildername',
            '-tag', 'buildbot.buildnumber=1337',
            '-tag', 'logdog.viewer_url=https://luci-milo.appspot.com/buildbot/'
                    'mastername/buildername/1337',
            '-service-account-json', 'creds.json',
            '-output-max-buffer-age', '30s',
            '-io-keepalive-stderr', '5m',
            'run',
            '-stdout', 'tee=stdout',
            '-stderr', 'tee=stderr',
            '-streamserver-uri', streamserver_uri,
            '--',
            os.path.join(cipd_dir, 'logdog_annotee.exe'),
                '-log-level', 'warning',
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
  @mock.patch('slave.logdog_bootstrap._get_service_account_json')
  @mock.patch('slave.logdog_bootstrap._get_params')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_bootstrap_command_mac_canary(self, tempdir, get_params,
                                        service_account, isfile):
    infra_platform.get.return_value = ('mac', 'x86_64', 64)

    recipe_cmd = ['recipes.py', 'recipe_params...']

    tempdir.return_value = 'foo'
    get_params.return_value = ldbs.Params(
        project='myproject', cipd_tag='canary',
        api=self.latest_api, mastername='mastername',
        buildername='buildername', buildnumber=1337, generation=None)
    service_account.return_value = 'creds.json'
    isfile.return_value = True

    bs = ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                        self.properties, recipe_cmd)

    # Check CIPD installation.
    cipd_dir = os.path.join(self.basedir, '.recipe_cipd')
    cipd_bootstrap_v2.install_cipd_packages.assert_called_once_with(
        cipd_dir,
        cipd.CipdPackage(
            name='infra/tools/luci/logdog/butler/${platform}',
            version='canary'),
        cipd.CipdPackage(
            name='infra/tools/luci/logdog/annotee/${platform}',
            version='canary'),
    )

    # Check bootstrap command.
    self.assertEqual(
        bs.cmd,
        [os.path.join(cipd_dir, 'logdog_butler'),
            '-log-level', 'warning',
            '-project', 'myproject',
            '-prefix', 'bb/mastername/buildername/1337',
            '-coordinator-host', 'logs.chromium.org',
            '-output', 'logdog',
            '-tag', 'buildbot.master=mastername',
            '-tag', 'buildbot.builder=buildername',
            '-tag', 'buildbot.buildnumber=1337',
            '-tag', 'logdog.viewer_url=https://luci-milo.appspot.com/buildbot/'
                    'mastername/buildername/1337',
            '-service-account-json', 'creds.json',
            '-output-max-buffer-age', '30s',
            '-io-keepalive-stderr', '5m',
            'run',
            '-stdout', 'tee=stdout',
            '-stderr', 'tee=stderr',
            '-streamserver-uri', 'unix:foo/butler.sock',
            '--',
            os.path.join(cipd_dir, 'logdog_annotee'),
                '-log-level', 'warning',
                '-name-base', 'recipes',
                '-print-summary',
                '-tee', 'annotations',
                '-json-args-path', self._tp('logdog_annotee_cmd.json'),
                '-result-path', self._tp('bootstrap_result.json'),
        ])

    service_account.assert_called_once_with(
        self.opts, ldbs._PLATFORM_CONFIG[('mac',)]['credential_path'])
    self._assertAnnoteeCommand(recipe_cmd)

  @mock.patch('os.path.isfile')
  @mock.patch('slave.logdog_bootstrap._get_service_account_json')
  @mock.patch('slave.logdog_bootstrap._get_params')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_bootstrap_command_win_canary(self, tempdir, get_params,
                                        service_account, isfile):
    infra_platform.get.return_value = ('win', 'x86_64', 64)

    recipe_cmd = ['recipes.py', 'recipe_params...']

    tempdir.return_value = 'foo'
    get_params.return_value = ldbs.Params(
        project='myproject', cipd_tag='canary',
        api=self.latest_api, mastername='mastername',
        buildername='buildername', buildnumber=1337, generation=None)
    service_account.return_value = 'creds.json'
    isfile.return_value = True

    bs = ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                        self.properties, recipe_cmd)

    # Check CIPD installation.
    cipd_dir = os.path.join(self.basedir, '.recipe_cipd')
    cipd_bootstrap_v2.install_cipd_packages.assert_called_once_with(
        cipd_dir,
        cipd.CipdPackage(
            name='infra/tools/luci/logdog/butler/${platform}',
            version='canary'),
        cipd.CipdPackage(
            name='infra/tools/luci/logdog/annotee/${platform}',
            version='canary'),
    )

    # Check bootstrap command.
    self.assertEqual(
        bs.cmd,
        [os.path.join(cipd_dir, 'logdog_butler.exe'),
            '-log-level', 'warning',
            '-project', 'myproject',
            '-prefix', 'bb/mastername/buildername/1337',
            '-coordinator-host', 'logs.chromium.org',
            '-output', 'logdog',
            '-tag', 'buildbot.master=mastername',
            '-tag', 'buildbot.builder=buildername',
            '-tag', 'buildbot.buildnumber=1337',
            '-tag', 'logdog.viewer_url=https://luci-milo.appspot.com/buildbot/'
                    'mastername/buildername/1337',
            '-service-account-json', 'creds.json',
            '-output-max-buffer-age', '30s',
            '-io-keepalive-stderr', '5m',
            'run',
            '-stdout', 'tee=stdout',
            '-stderr', 'tee=stderr',
            '-streamserver-uri', 'net.pipe:LUCILogDogButler',
            '--',
            os.path.join(cipd_dir, 'logdog_annotee.exe'),
                '-log-level', 'warning',
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
  @mock.patch('slave.logdog_bootstrap._get_service_account_json')
  @mock.patch('slave.logdog_bootstrap._get_params')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_registered_apis_work(self, tempdir, get_params, service_account,
                                isfile):
    tempdir.return_value = 'foo'
    isfile.return_value = True
    service_account.return_value = 'creds.json'

    for api in sorted(ldbs._CIPD_TAG_API_MAP.values()):
      get_params.return_value = self.base._replace(api=api)
      ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                     self.properties, [])

  def test_get_bootstrap_result(self):
    mo = mock.mock_open(read_data='{"return_code": 1337}')
    with mock.patch('slave.logdog_bootstrap.open', mo, create=True):
      bs = ldbs.BootstrapState(None, [], '/foo/bar')
      self.assertEqual(bs.get_result(), 1337)

    mo = mock.mock_open(read_data='!!! NOT JSON? !!!')
    with mock.patch('slave.logdog_bootstrap.open', mo, create=True):
      bs = ldbs.BootstrapState(None, [], '/foo/bar')
      self.assertRaises(ldbs.BootstrapError, bs.get_result)

    mo = mock.mock_open(read_data='{"invalid": "json"}')
    with mock.patch('slave.logdog_bootstrap.open', mo, create=True):
      bs = ldbs.BootstrapState(None, [], '/foo/bar')
      self.assertRaises(ldbs.BootstrapError, bs.get_result)

    mo = mock.mock_open()
    with mock.patch('slave.logdog_bootstrap.open', mo, create=True):
      mo.side_effect = IOError('Test not found')
      self.assertRaises(ldbs.BootstrapError, bs.get_result)

  def test_bootstrap_annotations(self):
    sio = StringIO.StringIO()
    stream = annotator.StructuredAnnotationStream(stream=sio)
    cfg = ldbs.Config(
        params=self.base,
        plat=None,
        host='example.com',
        prefix='foo/bar',
        tags=None,
        service_account_path=None,
    )
    bs = ldbs.BootstrapState(cfg, [], '/foo/bar')
    bs.annotate(stream)

    lines = [l for l in sio.getvalue().splitlines() if l]
    self.assertEqual(lines, [
        '@@@SEED_STEP LogDog Bootstrap@@@',
        '@@@STEP_CURSOR LogDog Bootstrap@@@',
        '@@@STEP_STARTED@@@',
        '@@@SET_BUILD_PROPERTY@logdog_project@"alpha"@@@',
        '@@@SET_BUILD_PROPERTY@logdog_prefix@"foo/bar"@@@',
        ('@@@SET_BUILD_PROPERTY@log_location@'
         '"logdog://example.com/alpha/foo/bar/+/recipes/annotations"@@@'),
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
    self.assertEqual(service_account_json, ':gce')

  @mock.patch('slave.logdog_bootstrap.get_config')
  def test_cipd_install_failure_raises_bootstrap_error(self, get_config):
    cipd_bootstrap_v2.install_cipd_packages.side_effect = (
        subprocess.CalledProcessError(0, [], 'PROCESS ERROR'))

    with self.assertRaises(ldbs.BootstrapError) as e:
      ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                    self.properties, [])

    self.assertEqual(e.exception.message, 'Failed to install CIPD packages.')
    cipd_bootstrap_v2.install_cipd_packages.assert_called_once()

  @mock.patch('slave.logdog_bootstrap._get_params')
  def test_will_not_bootstrap_if_recursive(self, get_params):
    get_params.side_effect = Exception('Tried to bootstrap')
    os.environ['LOGDOG_STREAM_PREFIX'] = 'foo'

    with self.assertRaises(ldbs.NotBootstrapped):
      ldbs.bootstrap(self.rt, self.opts, self.basedir, self.tdir,
                    self.properties, [])

  @mock.patch('slave.logdog_bootstrap._get_params')
  def test_will_not_bootstrap_if_disabled(self, get_params):
    get_params.side_effect = Exception('Tried to bootstrap')
    opts = self.opts._replace(logdog_disable=True)

    with self.assertRaises(ldbs.NotBootstrapped):
      ldbs.bootstrap(self.rt, opts, self.basedir, self.tdir,
                     self.properties, [])


class TestPublicParams(unittest.TestCase):

  def setUp(self):
    logging.basicConfig(level=logging.DEBUG)

  @unittest.skip("https://crbug.com/835262")
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
