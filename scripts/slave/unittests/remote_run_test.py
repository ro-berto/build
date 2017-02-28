#!/usr/bin/env python

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests that the tools/build remote_run wrapper actually runs."""

import base64
import collections
import json
import logging
import os
import StringIO
import subprocess
import sys
import tempfile
import unittest
import zlib

import test_env  # pylint: disable=W0403,W0611

import mock
from common import annotator
from common import env
from slave import remote_run
from slave import logdog_bootstrap
from slave import robust_tempdir
from slave import update_scripts

# <build>/scripts/slave
BASE_DIR = os.path.join(env.Build, 'scripts', 'slave')


MockOptions = collections.namedtuple('MockOptions', (
  'dry_run', 'factory_properties', 'build_properties', 'logdog_disable',
  'kitchen', 'repository', 'revision', 'use_gitiles', 'recipe',
  'logdog_debug_out_file',
))


class RemoteRunTest(unittest.TestCase):

  class TestException(Exception):
    pass

  REMOTE_REPO = 'https://chromium.googlesource.com/chromium/tools/build.git'

  def setUp(self):
    # Because we modify system-level globals (yay!)
    self._orig_env = os.environ.copy()

  def tearDown(self):
    os.environ = self._orig_env

  def test_example(self):
    build_properties = {
      'mastername': 'tryserver.chromium.linux',
      'buildername': 'builder',
      'slavename': 'bot42-m1',
      'true_prop': True,
      'num_prop': 123,
      'string_prop': '321',
      'dict_prop': {'foo': 'bar'},
    }

    script_path = os.path.join(BASE_DIR, 'remote_run.py')
    prop_gz = base64.b64encode(zlib.compress(json.dumps(build_properties)))
    exit_code = subprocess.call([
        sys.executable, script_path,
        '--build-properties-gz=%s' % (prop_gz,),
        '--recipe', 'remote_run_test',
        '--repository', self.REMOTE_REPO,
        ])
    self.assertEqual(exit_code, 0)

  def test_example_canary(self):
    build_properties = {
      'mastername': 'tryserver.chromium.linux',
      'buildername': 'builder',
      'slavename': 'bot42-m1',
      'true_prop': True,
      'num_prop': 123,
      'string_prop': '321',
      'dict_prop': {'foo': 'bar'},
    }

    # Emulate BuildBot enviornment.
    proc_env = os.environ.copy()
    proc_env['BUILDBOT_SLAVENAME'] = build_properties['slavename']

    script_path = os.path.join(BASE_DIR, 'remote_run.py')
    prop_gz = base64.b64encode(zlib.compress(json.dumps(build_properties)))
    exit_code = subprocess.call([
        sys.executable, script_path,
        '--build-properties-gz=%s' % (prop_gz,),
        '--recipe', 'remote_run_test',
        '--repository', self.REMOTE_REPO,
        '--canary',
        ],
        env=proc_env)
    self.assertEqual(exit_code, 0)

  @mock.patch('slave.remote_run._call')
  @mock.patch('slave.update_scripts._run_command')
  @mock.patch('sys.platform', return_value='win')
  @mock.patch('tempfile.mkstemp', side_effect=Exception('failure'))
  def test_update_scripts_must_run(self, _tempfile_mkstemp, _sys_platform,
                                   update_scripts_run_command, remote_run_call):
    update_scripts_run_command.return_value = (0, "")
    remote_run_call._call.return_value = 0

    remote_run.shell_main(['remote_run.py', 'foo'])

    gclient_path = os.path.join(env.Build, os.pardir, 'depot_tools',
                                'gclient.bat')
    update_scripts_run_command.assert_has_calls([
        mock.call([gclient_path, 'sync',
                   '--force', '--delete_unversioned_trees',
                   '--break_repo_locks', '--verbose', '--jobs=2'],
                  cwd=env.Build),
        ])


class RemoteRunExecTest(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR+1)

    self.maxDiff = None
    map(lambda x: x.start(), (
        mock.patch('slave.remote_run._call'),
        mock.patch('slave.remote_run._get_cipd_pins'),
        mock.patch('slave.cipd_bootstrap_v2.high_level_ensure_cipd_client'),
        mock.patch('slave.monitoring_utils.write_build_monitoring_event'),
        mock.patch('os.path.exists'),
        ))
    self.addCleanup(mock.patch.stopall)

    self.rt = robust_tempdir.RobustTempdir(prefix='remote_run_test')
    self.addCleanup(self.rt.close)

    self.stream_output = StringIO.StringIO()
    self.stream = annotator.StructuredAnnotationStream(
        stream=self.stream_output)
    self.basedir = self.rt.tempdir()
    self.tempdir = self.rt.tempdir()
    self.build_data_dir = self.rt.tempdir()
    self.opts = MockOptions(
        dry_run=False,
        logdog_disable=False,
        factory_properties={},
        build_properties={
          'slavename': 'bot42-m1',
          'mastername': 'tryserver.chromium.linux',
          'buildername': 'builder',
        },
        kitchen=None,
        repository='https://example.com/repo.git',
        revision=None,
        use_gitiles=True,
        recipe='example/recipe',
        logdog_debug_out_file=None,
    )
    self.rpy_path = os.path.join(env.Build, 'scripts', 'slave', 'recipes.py')

    self.recipe_remote_args = [
        sys.executable, self._bp('.remote_run_cipd', 'recipes.py'),
        '--operational-args-path', self._tp('engine_flags.json'),
        '--verbose', 'remote',
        '--repository', self.opts.repository,
        '--workdir', self._tp('rw'),
        '--use-gitiles',
    ]

    self.kitchen_args = [
        self._bp('.remote_run_cipd', 'kitchen'),
        '-log-level', 'info',
        'cook',
        '-mode', 'buildbot',
        '-recipe-engine-path', self._bp('.remote_run_cipd'),
        '-output-result-json', self._tp('recipe_result.json'),
        '-properties-file', self._tp('remote_run_properties.json'),
        '-recipe', self.opts.recipe,
        '-repository', self.opts.repository,
        '-temp-dir', self._tp('t'),
        '-checkout-dir', self._tp('rw'),
        '-workdir', self._tp('w'),
        '-allow-gitiles',
    ]

    self.recipe_args = [
        '--operational-args-path', self._tp('engine_flags.json'),
        '--verbose', 'run',
        '--properties-file', self._tp('remote_run_properties.json'),
        '--workdir', self._tp('w'),
        '--output-result-json', self._tp('recipe_result.json'),
        self.opts.recipe,
    ]

    # Use public recipes.py path.
    os.path.exists.return_value = False

    # Easily-configurable CIPD pins.
    self.cipd_pins = remote_run._STABLE_CIPD_PINS
    remote_run._get_cipd_pins = lambda _args, _mastername: self.cipd_pins

    # Written via '_write_recipe_result'.
    self.recipe_result = None

  def _bp(self, *p):
    return os.path.join(*((self.basedir,) + p))

  def _tp(self, *p):
    return os.path.join(*((self.tempdir,) + p))

  @staticmethod
  def _default_namedtuple(typ, default=None):
    return typ(**{f: default for f in typ._fields})

  def _write_recipe_result(self):
    with open(self._tp('recipe_result.json'), 'w') as fd:
      json.dump(self.recipe_result, fd)

  @mock.patch('slave.logdog_bootstrap.bootstrap',
              side_effect=logdog_bootstrap.NotBootstrapped())
  @mock.patch('slave.remote_run._install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_exec_without_logdog(self, rt_tempdir, _install_cipd_packages,
                               _logdog_bootstrap):
    remote_run._call.return_value = 0
    rt_tempdir.side_effect = [self.tempdir, self.build_data_dir]
    self._write_recipe_result()

    rv = remote_run._exec_recipe(self.opts, self.rt, self.stream, self.basedir)
    self.assertEqual(rv, 0)

    args = self.recipe_remote_args + ['--'] + self.recipe_args
    remote_run._call.assert_called_once_with(args)

  @mock.patch('slave.logdog_bootstrap.bootstrap',
              side_effect=logdog_bootstrap.NotBootstrapped())
  @mock.patch('slave.remote_run._install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_kitchen_exec_without_logdog(self, rt_tempdir, _install_cipd_packages,
                                      _logdog_bootstrap):
    # Force Kitchen enable.
    self.cipd_pins = remote_run._CANARY_CIPD_PINS._replace(kitchen='enable')

    remote_run._call.return_value = 0
    rt_tempdir.side_effect = [self.tempdir, self.build_data_dir]
    self._write_recipe_result()

    rv = remote_run._exec_recipe(self.opts, self.rt, self.stream, self.basedir)
    self.assertEqual(rv, 0)

    remote_run._call.assert_called_once_with(self.kitchen_args)

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  @mock.patch('slave.logdog_bootstrap.BootstrapState.get_result')
  @mock.patch('slave.remote_run._install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_exec_with_logdog(self, rt_tempdir, _install_cipd_packages,
                            _logdog_bootstrap_result, bootstrap):

    args = self.recipe_remote_args + ['--'] + self.recipe_args
    cfg = self._default_namedtuple(logdog_bootstrap.Config)._replace(
        params=self._default_namedtuple(logdog_bootstrap.Params)._replace(
          project="project",
        ),
        prefix="prefix",
        host="example.com",
    )
    bootstrap.return_value = logdog_bootstrap.BootstrapState(
        cfg, ['logdog_bootstrap'] + args, '/path/to/result.json')
    bootstrap.return_value.get_result.return_value = 0

    remote_run._call.return_value = 0
    rt_tempdir.side_effect = [self.tempdir, self.build_data_dir]
    self._write_recipe_result()

    rv = remote_run._exec_recipe(self.opts, self.rt, self.stream, self.basedir)
    self.assertEqual(rv, 0)

    remote_run._call.assert_called_once_with(bootstrap.return_value.cmd)
    self.assertEqual(
        [l for l in self.stream_output.getvalue().splitlines() if l],
        [
            '@@@SEED_STEP LogDog Bootstrap@@@',
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@logdog_project@"project"@@@',
            '@@@SET_BUILD_PROPERTY@logdog_prefix@"prefix"@@@',
            ('@@@SET_BUILD_PROPERTY@logdog_annotation_url@'
             '"logdog://example.com/project/prefix/+/recipes/annotations"@@@'),
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_CLOSED@@@',
        ]
    )

  @mock.patch('slave.logdog_bootstrap.get_config')
  @mock.patch('slave.logdog_bootstrap.BootstrapState.get_result')
  @mock.patch('slave.remote_run._install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_kitchen_exec_with_logdog(self, rt_tempdir, _install_cipd_packages,
                                   _logdog_bootstrap_result, get_config):
    # Force Kitchen enable.
    self.cipd_pins = remote_run._CANARY_CIPD_PINS._replace(kitchen='enable')

    cfg = self._default_namedtuple(logdog_bootstrap.Config)._replace(
        params=self._default_namedtuple(logdog_bootstrap.Params)._replace(
          project="project",
        ),
        prefix="prefix",
        host="example.com",
    )
    get_config.return_value = cfg

    remote_run._call.return_value = 0
    rt_tempdir.side_effect = [self.tempdir, self.build_data_dir]
    self._write_recipe_result()

    rv = remote_run._exec_recipe(self.opts, self.rt, self.stream, self.basedir)
    self.assertEqual(rv, 0)

    kitchen_args = self.kitchen_args + [
        '-logdog-annotation-url', logdog_bootstrap.get_annotation_url(cfg),
    ]

    remote_run._call.assert_called_once_with(kitchen_args)
    self.assertEqual(
        [l for l in self.stream_output.getvalue().splitlines() if l],
        [
            '@@@SEED_STEP LogDog Bootstrap@@@',
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@logdog_project@"project"@@@',
            '@@@SET_BUILD_PROPERTY@logdog_prefix@"prefix"@@@',
            ('@@@SET_BUILD_PROPERTY@logdog_annotation_url@'
             '"logdog://example.com/project/prefix/+/recipes/annotations"@@@'),
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_CLOSED@@@',
        ]
    )


if __name__ == '__main__':
  unittest.main()
