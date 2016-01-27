#!/usr/bin/env python

# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests that the tools/build annotated_run wrapper actually runs."""

import collections
import contextlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest

import test_env  # pylint: disable=W0403,W0611

import mock
from common import chromium_utils
from common import env
from slave import annotated_run
from slave import gce

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MockOptions = collections.namedtuple('MockOptions',
    ('dry_run', 'logdog_force', 'logdog_butler_path', 'logdog_annotee_path',
     'logdog_verbose', 'logdog_service_account_json'))


class AnnotatedRunTest(unittest.TestCase):
  def test_example(self):
    build_properties = {
      'recipe': 'annotated_run_test',
      'true_prop': True,
      'num_prop': 123,
      'string_prop': '321',
      'dict_prop': {'foo': 'bar'},
    }

    script_path = os.path.join(BASE_DIR, 'annotated_run.py')
    exit_code = subprocess.call([
        'python', script_path,
        '--build-properties=%s' % json.dumps(build_properties)])
    self.assertEqual(exit_code, 0)

  @mock.patch('slave.annotated_run._run_command')
  @mock.patch('slave.annotated_run.main')
  @mock.patch('sys.platform', return_value='win')
  @mock.patch('tempfile.mkstemp', side_effect=Exception('failure'))
  @mock.patch('os.environ', {})
  def test_update_scripts_must_run(self, _tempfile_mkstemp, _sys_platform,
                                   main, run_command):
    annotated_run.main.side_effect = Exception('Test error!')
    annotated_run._run_command.return_value = (0, "")
    annotated_run.shell_main(['annotated_run.py', 'foo'])

    gclient_path = os.path.join(env.Build, os.pardir, 'depot_tools',
                                'gclient.bat')
    run_command.assert_has_calls([
        mock.call([gclient_path, 'sync', '--force', '--verbose', '--jobs=2'],
                  cwd=env.Build),
        mock.call([sys.executable, 'annotated_run.py', 'foo']),
        ])
    main.assert_not_called()


class _AnnotatedRunExecTestBase(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR+1)

    self.maxDiff = None
    self._patchers = []
    map(self._patch, (
        mock.patch('slave.annotated_run._run_command'),
        mock.patch('os.path.exists'),
        mock.patch('os.getcwd'),
        ))

    self.rt = annotated_run.Runtime()
    self.tdir = self.rt.tempdir()
    self.opts = MockOptions(
        dry_run=False,
        logdog_force=False,
        logdog_annotee_path=None,
        logdog_butler_path=None,
        logdog_verbose=False,
        logdog_service_account_json=None)
    self.config = annotated_run.Config(
        run_cmd=['run.py'],
        logdog_pubsub=None,
        logdog_platform=None,
    )
    self.properties = {
      'recipe': 'example/recipe',
      'mastername': 'master.random',
      'buildername': 'builder',
    }
    self.cwd = os.path.join('home', 'user')
    self.rpy_path = os.path.join(env.Build, 'scripts', 'slave', 'recipes.py')
    self.recipe_args = [
        sys.executable, '-u', self.rpy_path, '--verbose', 'run',
        '--workdir=%s' % (self.cwd,),
        '--properties-file=%s' % (self._tp('recipe_properties.json'),),
        'example/recipe']

    # Use public recipes.py path.
    os.getcwd.return_value = self.cwd
    os.path.exists.return_value = False

  def tearDown(self):
    self.rt.close()
    for p in reversed(self._patchers):
      p.stop()

  def _tp(self, *p):
    return os.path.join(*((self.tdir,) + p))

  def _patch(self, patcher):
    self._patchers.append(patcher)
    patcher.start()
    return patcher

  def _assertRecipeProperties(self, value):
    # Double-translate "value", since JSON converts strings to unicode.
    value = json.loads(json.dumps(value))
    with open(self._tp('recipe_properties.json')) as fd:
      self.assertEqual(json.load(fd), value)


class AnnotatedRunExecTest(_AnnotatedRunExecTestBase):

  def test_exec_successful(self):
    annotated_run._run_command.return_value = (0, '')

    rv = annotated_run._exec_recipe(self.rt, self.opts, self.tdir, self.config,
                                    self.properties)
    self.assertEqual(rv, 0)
    self._assertRecipeProperties(self.properties)

    annotated_run._run_command.assert_called_once_with(self.recipe_args,
                                                       dry_run=False)


class AnnotatedRunLogDogExecTest(_AnnotatedRunExecTestBase):

  def setUp(self):
    super(AnnotatedRunLogDogExecTest, self).setUp()
    self._orig_whitelist = annotated_run.LOGDOG_WHITELIST_MASTER_BUILDERS
    annotated_run.LOGDOG_WHITELIST_MASTER_BUILDERS = {
      'master.some': [
        'yesbuilder',
      ],

      'master.all': [
        annotated_run.WHITELIST_ALL,
      ],
    }
    self.properties.update({
      'mastername': 'master.some',
      'buildername': 'nobuilder',
      'buildnumber': 1337,
    })
    self.config = self.config._replace(
        logdog_pubsub=annotated_run.PubSubConfig(project='test', topic='logs'),
        logdog_platform=annotated_run.LogDogPlatform(
            butler=annotated_run.CipdBinary('cipd/butler', 'head', 'butler'),
            annotee=annotated_run.CipdBinary('cipd/annotee', 'head', 'annotee'),
            credential_path=os.path.join('path', 'to', 'creds.json'),
            streamserver='unix',
        ),
    )
    self.is_gce = False

    def is_gce():
      return self.is_gce
    is_gce_patch = mock.patch('slave.gce.Authenticator.is_gce',
                              side_effect=is_gce)
    is_gce_patch.start()
    self._patchers.append(is_gce_patch)

  def tearDown(self):
    annotated_run.LOGDOG_WHITELIST_MASTER_BUILDERS = self._orig_whitelist
    super(AnnotatedRunLogDogExecTest, self).tearDown()

  def _assertAnnoteeCommand(self, value):
    # Double-translate "value", since JSON converts strings to unicode.
    value = json.loads(json.dumps(value))
    with open(self._tp('logdog_bootstrap', 'annotee_cmd.json')) as fd:
      self.assertEqual(json.load(fd), value)

  def test_should_run_logdog(self):
    self.assertFalse(annotated_run._should_run_logdog({
      'mastername': 'master.undefined', 'buildername': 'any'}))
    self.assertFalse(annotated_run._should_run_logdog({
      'mastername': 'master.some', 'buildername': 'nobuilder'}))
    self.assertTrue(annotated_run._should_run_logdog({
      'mastername': 'master.some', 'buildername': 'yesbuilder'}))
    self.assertTrue(annotated_run._should_run_logdog({
      'mastername': 'master.all', 'buildername': 'anybuilder'}))

  @mock.patch('slave.annotated_run._get_service_account_json')
  def test_exec_with_whitelist_builder_runs_logdog(self, service_account):
    self.properties['buildername'] = 'yesbuilder'

    butler_path = self._tp('logdog_bootstrap', 'cipd', 'butler')
    annotee_path = self._tp('logdog_bootstrap', 'cipd', 'annotee')
    service_account.return_value = 'creds.json'
    annotated_run._run_command.return_value = (0, '')

    self._patch(mock.patch('tempfile.mkdtemp', return_value='foo'))
    rv = annotated_run._exec_recipe(self.rt, self.opts, self.tdir, self.config,
                                    self.properties)
    self.assertEqual(rv, 0)

    streamserver_uri = 'unix:%s' % (os.path.join('foo', 'butler.sock'),)
    service_account.assert_called_once_with(
        self.opts, self.config.logdog_platform.credential_path)
    annotated_run._run_command.assert_called_with(
        [butler_path,
            '-prefix', 'bb/master.some/yesbuilder/1337',
            '-output', 'pubsub,project="test",topic="logs"',
            '-service-account-json', 'creds.json',
            'run',
            '-stdout', 'tee=stdout',
            '-stderr', 'tee=stderr',
            '-streamserver-uri', streamserver_uri,
            '--',
            annotee_path,
                '-butler-stream-server', streamserver_uri,
                '-annotate', 'tee',
                '-name-base', 'recipes',
                '-print-summary',
                '-tee',
                '-json-args-path', self._tp('logdog_bootstrap',
                                            'annotee_cmd.json'),
        ],
        dry_run=False)
    self._assertRecipeProperties(self.properties)
    self._assertAnnoteeCommand(self.recipe_args)

  @mock.patch('slave.annotated_run._logdog_bootstrap', return_value=0)
  def test_runs_bootstrap_when_forced(self, lb):
    opts = self.opts._replace(logdog_force=True)
    rv = annotated_run._exec_recipe(self.rt, opts, self.tdir, self.config,
                                    self.properties)
    self.assertEqual(rv, 0)
    lb.assert_called_once()
    annotated_run._run_command.assert_called_once()

  @mock.patch('slave.annotated_run._logdog_bootstrap', return_value=2)
  def test_forwards_error_code(self, lb):
    opts = self.opts._replace(
        logdog_force=True)
    rv = annotated_run._exec_recipe(self.rt, opts, self.tdir, self.config,
                                    self.properties)
    self.assertEqual(rv, 2)
    lb.assert_called_once()

  @mock.patch('slave.annotated_run._logdog_bootstrap',
              side_effect=Exception('Unhandled situation.'))
  def test_runs_directly_if_bootstrap_fails(self, lb):
    annotated_run._run_command.return_value = (123, '')

    rv = annotated_run._exec_recipe(self.rt, self.opts, self.tdir, self.config,
                                    self.properties)
    self.assertEqual(rv, 123)

    lb.assert_called_once()
    annotated_run._run_command.assert_called_once_with(self.recipe_args,
                                                       dry_run=False)

  @mock.patch('slave.annotated_run._logdog_install_cipd')
  @mock.patch('slave.annotated_run._get_service_account_json')
  def test_runs_directly_if_logdog_error(self, service_account, cipd):
    self.properties['buildername'] = 'yesbuilder'

    cipd.return_value = ('butler', 'annotee')
    service_account.return_value = 'creds.json'
    def error_for_logdog(args, **kw):
      if len(args) > 0 and args[0] == 'butler':
        return (250, '')
      return (4, '')
    annotated_run._run_command.side_effect = error_for_logdog

    self._patch(mock.patch('tempfile.mkdtemp', return_value='foo'))
    rv = annotated_run._exec_recipe(self.rt, self.opts, self.tdir, self.config,
                                    self.properties)
    self.assertEqual(rv, 4)

    streamserver_uri = 'unix:%s' % (os.path.join('foo', 'butler.sock'),)
    service_account.assert_called_once_with(
        self.opts, self.config.logdog_platform.credential_path)
    annotated_run._run_command.assert_has_calls([
        mock.call([
            'butler',
            '-prefix', 'bb/master.some/yesbuilder/1337',
            '-output', 'pubsub,project="test",topic="logs"',
            '-service-account-json', 'creds.json',
            'run',
            '-stdout', 'tee=stdout',
            '-stderr', 'tee=stderr',
            '-streamserver-uri', streamserver_uri,
            '--',
            'annotee',
                '-butler-stream-server', streamserver_uri,
                '-annotate', 'tee',
                '-name-base', 'recipes',
                '-print-summary',
                '-tee',
                '-json-args-path', self._tp('logdog_bootstrap',
                                            'annotee_cmd.json'),
        ], dry_run=False),
        mock.call(self.recipe_args, dry_run=False),
    ])

  @mock.patch('os.path.isfile')
  def test_can_find_credentials(self, isfile):
    isfile.return_value = True

    service_account_json = annotated_run._get_service_account_json(
        self.opts, 'creds.json')
    self.assertEqual(service_account_json, 'creds.json')

  def test_uses_no_credentials_on_gce(self):
    self.is_gce = True
    service_account_json = annotated_run._get_service_account_json(
        self.opts, ('foo', 'bar'))
    self.assertIsNone(service_account_json)

  def test_cipd_install(self):
    annotated_run._run_command.return_value = (0, '')

    pkgs = annotated_run._logdog_install_cipd(self.tdir,
        annotated_run.CipdBinary('infra/foo', 'v0', 'foo'),
        annotated_run.CipdBinary('infra/bar', 'v1', 'baz'),
        )
    self.assertEqual(pkgs, (self._tp('foo'), self._tp('baz')))

    annotated_run._run_command.assert_called_once_with([
      sys.executable,
       os.path.join(env.Build, 'scripts', 'slave', 'cipd.py'),
       '--dest-directory', self.tdir,
       '--json-output', os.path.join(self.tdir, 'packages.json'),
       '-P', 'infra/foo@v0',
       '-P', 'infra/bar@v1',
    ])

  def test_cipd_install_failure_raises_bootstrap_error(self):
    annotated_run._run_command.return_value = (1, '')

    self.assertRaises(annotated_run.LogDogBootstrapError,
        annotated_run._logdog_install_cipd,
        self.tdir,
        annotated_run.CipdBinary('infra/foo', 'v0', 'foo'),
        annotated_run.CipdBinary('infra/bar', 'v1', 'baz'),
    )


if __name__ == '__main__':
  unittest.main()
