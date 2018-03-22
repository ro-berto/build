#!/usr/bin/env vpython

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

import mock

import test_env  # pylint: disable=relative-import

from common import annotator
from common import chromium_utils
from common import env
from slave import cleanup_temp
from slave import logdog_bootstrap
from slave import remote_run
from slave import robust_tempdir
from slave import update_scripts
from slave.unittests.utils import FakeBuildRootTestCase

# <build>/scripts/slave
BASE_DIR = os.path.join(env.Build, 'scripts', 'slave')


MockOptions = collections.namedtuple('MockOptions', (
  'dry_run', 'factory_properties', 'build_properties', 'logdog_disable',
  'kitchen', 'repository', 'revision', 'use_gitiles', 'recipe',
  'logdog_debug_out_file', 'canary',
))


class RemoteRunTest(FakeBuildRootTestCase):

  REMOTE_REPO = 'https://chromium.googlesource.com/chromium/tools/build.git'

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

    # Emulate BuildBot enviornment w/ active subdir.
    proc_env = self.get_test_env(
        INFRA_BUILDBOT_SLAVE_ACTIVE_SUBDIR='foo')

    script_path = os.path.join(BASE_DIR, 'remote_run.py')
    prop_gz = base64.b64encode(zlib.compress(json.dumps(build_properties)))
    exit_code = subprocess.call([
        'python', script_path,
        '--build-properties-gz=%s' % (prop_gz,),
        '--recipe', 'remote_run_test',
        '--repository', self.REMOTE_REPO,
        ],
        cwd=self.fake_build_root,
        env=proc_env,
    )
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
    proc_env = self.get_test_env(
        BUILDBOT_SLAVENAME=build_properties['slavename'],
        # No active subdir.
        INFRA_BUILDBOT_SLAVE_ACTIVE_SUBDIR='')

    script_path = os.path.join(BASE_DIR, 'remote_run.py')
    prop_gz = base64.b64encode(zlib.compress(json.dumps(build_properties)))
    exit_code = subprocess.call([
        'python', script_path,
        '--build-properties-gz=%s' % (prop_gz,),
        '--recipe', 'remote_run_test',
        '--repository', self.REMOTE_REPO,
        '--canary',
        ],
        cwd=self.fake_build_root,
        env=proc_env,
    )
    self.assertEqual(exit_code, 0)


class RemoteRunExecTest(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR+1)

    self._orig_env = os.environ.copy()
    os.environ = {'FOO': 'BAR', 'PYTHONPATH': '/pants'}

    self.maxDiff = None
    map(lambda x: x.start(), (
        mock.patch('slave.remote_run._call'),
        mock.patch('slave.remote_run._get_is_canary'),
        mock.patch('slave.remote_run._get_is_kitchen'),
        mock.patch('slave.monitoring_utils.write_build_monitoring_event'),
        mock.patch('os.path.exists'),
        mock.patch('common.chromium_utils.RemoveDirectory'),
        mock.patch('common.chromium_utils.MoveFile'),
        mock.patch('common.chromium_utils.GetActiveSubdir'),
        ))

    func = mock.patch(
      'slave.cipd_bootstrap_v2.high_level_ensure_cipd_client').start()
    func.return_value = [
      'cipd_path_tools',
      os.path.join('cipd_path_tools', 'bin'),
    ]

    self.addCleanup(mock.patch.stopall)

    self.rt = robust_tempdir.RobustTempdir(prefix='remote_run_test')
    self.addCleanup(self.rt.close)

    self.stream_output = StringIO.StringIO()
    self.stream = annotator.StructuredAnnotationStream(
        stream=self.stream_output)
    self.basedir = self.rt.tempdir()

    build_root = self.rt.tempdir()
    self.buildbot_build_dir = remote_run._ensure_directory(build_root, 'build')
    self.cleanup_dir = remote_run._ensure_directory(build_root, 'build.dead')
    self.cache_dir = remote_run._ensure_directory(build_root, 'cache')
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
        canary=None,
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
        '-output-result-json', self._tp('kitchen_result.json'),
        '-properties-file', self._tp('remote_run_properties.json'),
        '-recipe', self.opts.recipe,
        '-repository', self.opts.repository,
        '-cache-dir', self.cache_dir,
        '-temp-dir', self._tp('t'),
        '-checkout-dir', self._tp('rw'),
        '-workdir', self._tp('w'),
    ]

    self.recipe_args = [
        '--operational-args-path', self._tp('engine_flags.json'),
        '--verbose', 'run',
        '--properties-file', self._tp('remote_run_properties.json'),
        '--workdir', self._tp('w'),
        '--output-result-json', self._tp('recipe_result.json'),
        self.opts.recipe,
    ]

    # No active subdir by default.
    chromium_utils.GetActiveSubdir.return_value = None

    # Easily-configurable CIPD pins.
    self.is_canary = False
    self.is_kitchen = False
    remote_run._get_is_canary.side_effect = lambda *_a: self.is_canary
    remote_run._get_is_kitchen.side_effect = lambda *_a: self.is_kitchen

    # Written via '_write_recipe_result'.
    self.recipe_result = None
    # Written via '_write_kitchen_result'.
    self.kitchen_result = None

  def tearDown(self):
    os.environ = self._orig_env

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

  def _write_kitchen_result(self):
    with open(self._tp('kitchen_result.json'), 'w') as fd:
      json.dump(self.kitchen_result, fd)

  @mock.patch('slave.update_scripts._run_command')
  @mock.patch('slave.remote_run.main')
  @mock.patch('sys.platform', return_value='win')
  @mock.patch('tempfile.mkstemp', side_effect=Exception('failure'))
  def test_update_scripts_must_run(self, _tempfile_mkstemp, _sys_platform,
                                   main, update_scripts_run_command):
    update_scripts_run_command.return_value = (0, "")
    remote_run._call.return_value = 0

    remote_run.shell_main([
        'remote_run.py',
        '--repository', 'foo',
        '--recipe', 'pants',
    ])

    gclient_path = os.path.join(env.Build, os.pardir, 'depot_tools',
                                'gclient.bat')
    update_scripts_run_command.assert_has_calls([
        mock.call([gclient_path, 'sync',
                   '--force', '--delete_unversioned_trees',
                   '--break_repo_locks', '--verbose', '--jobs=2',
                   '--disable-syntax-validation'],
                  cwd=env.Build),
        ])
    self.assertFalse(main.called)

  @mock.patch('slave.logdog_bootstrap.bootstrap',
              side_effect=logdog_bootstrap.NotBootstrapped())
  @mock.patch('slave.cipd_bootstrap_v2.install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_exec_without_logdog(self, rt_tempdir, _install_cipd_packages,
                               _logdog_bootstrap):
    remote_run._call.return_value = 0
    rt_tempdir.side_effect = [self.tempdir, self.build_data_dir]
    self.recipe_result = {}
    self._write_recipe_result()

    rv = remote_run._exec_recipe(
        self.opts, self.rt, self.stream, self.basedir, self.buildbot_build_dir,
        self.cleanup_dir, self.cache_dir)
    self.assertEqual(rv, 0)

    args = self.recipe_remote_args + ['--'] + self.recipe_args
    remote_run._call.assert_called_once_with(args)

  @mock.patch('slave.logdog_bootstrap.bootstrap',
              side_effect=logdog_bootstrap.NotBootstrapped())
  @mock.patch('slave.cipd_bootstrap_v2.install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_kitchen_exec_without_logdog(self, rt_tempdir, _install_cipd_packages,
                                      _logdog_bootstrap):
    self.is_kitchen = True

    remote_run._call.return_value = 0
    rt_tempdir.side_effect = [self.tempdir, self.build_data_dir]
    self._write_kitchen_result()

    opts = self.opts._replace(revision='refs/heads/somebranch')
    rv = remote_run._exec_recipe(
        opts, self.rt, self.stream, self.basedir, self.buildbot_build_dir,
        self.cleanup_dir, self.cache_dir)
    self.assertEqual(rv, 0)

    kitchen_args = self.kitchen_args + [
        '-revision', 'refs/heads/somebranch',
    ]
    kitchen_env = os.environ.copy()
    kitchen_env.pop('PYTHONPATH', None)

    remote_run._call.assert_called_once_with(kitchen_args, env=kitchen_env)

  @mock.patch('slave.logdog_bootstrap.bootstrap',
              side_effect=logdog_bootstrap.NotBootstrapped())
  @mock.patch('slave.cipd_bootstrap_v2.install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_kitchen_exec_canary_without_logdog(self, rt_tempdir,
                                              _install_cipd_packages,
                                              _logdog_bootstrap):
    self.is_canary = True
    self.is_kitchen = True

    remote_run._call.return_value = 0
    rt_tempdir.side_effect = [self.tempdir, self.build_data_dir]
    self._write_kitchen_result()

    opts = self.opts._replace(revision='refs/heads/somebranch')
    rv = remote_run._exec_recipe(
        opts, self.rt, self.stream, self.basedir, self.buildbot_build_dir,
        self.cleanup_dir, self.cache_dir)
    self.assertEqual(rv, 0)

    kitchen_args = self.kitchen_args + [
        '-revision', 'refs/heads/somebranch',
    ]
    kitchen_env = os.environ.copy()
    kitchen_env.pop('PYTHONPATH', None)

    remote_run._call.assert_called_once_with(kitchen_args, env=kitchen_env)

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  @mock.patch('slave.logdog_bootstrap.BootstrapState.get_result')
  @mock.patch('slave.cipd_bootstrap_v2.install_cipd_packages')
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
    self.recipe_result = {}
    self._write_recipe_result()

    rv = remote_run._exec_recipe(
        self.opts, self.rt, self.stream, self.basedir, self.buildbot_build_dir,
        self.cleanup_dir, self.cache_dir)
    self.assertEqual(rv, 0)

    remote_run._call.assert_called_once_with(bootstrap.return_value.cmd)
    self.assertEqual(
        [l for l in self.stream_output.getvalue().splitlines() if l],
        [
            '@@@SEED_STEP LUCI Migration@@@',
            '@@@STEP_CURSOR LUCI Migration@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@$recipe_engine/runtime@{"is_experimental":'
              ' false, "is_luci": false}@@@',
            '@@@SET_BUILD_PROPERTY@luci_migration@{"status": "error", "error":'
              ' "Insufficient properties."}@@@',
            '@@@STEP_CURSOR LUCI Migration@@@',
            '@@@STEP_CLOSED@@@',
            '@@@SEED_STEP LogDog Bootstrap@@@',
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@logdog_project@"project"@@@',
            '@@@SET_BUILD_PROPERTY@logdog_prefix@"prefix"@@@',
            ('@@@SET_BUILD_PROPERTY@log_location@'
             '"logdog://example.com/project/prefix/+/recipes/annotations"@@@'),
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_CLOSED@@@',
        ]
    )

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  @mock.patch('slave.logdog_bootstrap.BootstrapState.get_result')
  @mock.patch('slave.cipd_bootstrap_v2.install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_exec_with_logdog_failed(self, rt_tempdir, _install_cipd_packages,
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
    self.recipe_result = {
        'failure': {
            'timeout': True,
        }
    }
    self._write_recipe_result()

    rv = remote_run._exec_recipe(
        self.opts, self.rt, self.stream, self.basedir, self.buildbot_build_dir,
        self.cleanup_dir, self.cache_dir)
    self.assertEqual(rv, 255)

    remote_run._call.assert_called_once_with(bootstrap.return_value.cmd)
    self.assertEqual(
        [l for l in self.stream_output.getvalue().splitlines() if l],
        [
            '@@@SEED_STEP LUCI Migration@@@',
            '@@@STEP_CURSOR LUCI Migration@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@$recipe_engine/runtime@{"is_experimental":'
              ' false, "is_luci": false}@@@',
            '@@@SET_BUILD_PROPERTY@luci_migration@{"status": "error", "error":'
              ' "Insufficient properties."}@@@',
            '@@@STEP_CURSOR LUCI Migration@@@',
            '@@@STEP_CLOSED@@@',
            '@@@SEED_STEP LogDog Bootstrap@@@',
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@logdog_project@"project"@@@',
            '@@@SET_BUILD_PROPERTY@logdog_prefix@"prefix"@@@',
            ('@@@SET_BUILD_PROPERTY@log_location@'
             '"logdog://example.com/project/prefix/+/recipes/annotations"@@@'),
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_CLOSED@@@',
        ]
    )

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  @mock.patch('slave.logdog_bootstrap.BootstrapState.get_result')
  @mock.patch('slave.cipd_bootstrap_v2.install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_exec(self, rt_tempdir, _install_cipd_packages,
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
    self.recipe_result = {}
    self._write_recipe_result()

    rv = remote_run._exec_recipe(
        self.opts, self.rt, self.stream, self.basedir, self.buildbot_build_dir,
        self.cleanup_dir, self.cache_dir)
    self.assertEqual(rv, 0)

    remote_run._call.assert_called_once_with(bootstrap.return_value.cmd)
    self.assertEqual(
        [l for l in self.stream_output.getvalue().splitlines() if l],
        [
            '@@@SEED_STEP LUCI Migration@@@',
            '@@@STEP_CURSOR LUCI Migration@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@$recipe_engine/runtime@{"is_experimental":'
              ' false, "is_luci": false}@@@',
            '@@@SET_BUILD_PROPERTY@luci_migration@{"status": "error", "error":'
              ' "Insufficient properties."}@@@',
            '@@@STEP_CURSOR LUCI Migration@@@',
            '@@@STEP_CLOSED@@@',
            '@@@SEED_STEP LogDog Bootstrap@@@',
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@logdog_project@"project"@@@',
            '@@@SET_BUILD_PROPERTY@logdog_prefix@"prefix"@@@',
            ('@@@SET_BUILD_PROPERTY@log_location@'
             '"logdog://example.com/project/prefix/+/recipes/annotations"@@@'),
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_CLOSED@@@',
        ]
    )

  @mock.patch('slave.logdog_bootstrap.get_config')
  @mock.patch('slave.logdog_bootstrap.BootstrapState.get_result')
  @mock.patch('slave.cipd_bootstrap_v2.install_cipd_packages')
  @mock.patch('slave.robust_tempdir.RobustTempdir.tempdir')
  def test_kitchen_exec_with_logdog(self, rt_tempdir, _install_cipd_packages,
                                   _logdog_bootstrap_result, get_config):
    self.is_kitchen = True

    cfg = self._default_namedtuple(logdog_bootstrap.Config)._replace(
        params=self._default_namedtuple(logdog_bootstrap.Params)._replace(
          project="project",
        ),
        prefix="prefix",
        host="example.com",
        tags=collections.OrderedDict((
          ('foo', 'bar'),
          ('baz', None),
        )),
        service_account_path='/path/to/service_account.json',
    )
    get_config.return_value = cfg

    remote_run._call.return_value = 0
    rt_tempdir.side_effect = [self.tempdir, self.build_data_dir]
    self._write_kitchen_result()

    opts = self.opts._replace(revision='origin/master')
    rv = remote_run._exec_recipe(
        opts, self.rt, self.stream, self.basedir, self.buildbot_build_dir,
        self.cleanup_dir, self.cache_dir)
    self.assertEqual(rv, 0)

    kitchen_args = self.kitchen_args + [
        '-logdog-only',
        '-logdog-annotation-url', logdog_bootstrap.get_annotation_url(cfg),
        '-luci-system-account-json', '/path/to/service_account.json',
        '-logdog-tag', 'foo=bar',
        '-logdog-tag', 'baz',
    ]
    kitchen_env = os.environ.copy()
    kitchen_env.pop('PYTHONPATH', None)

    remote_run._call.assert_called_once_with(kitchen_args, env=kitchen_env)
    self.assertEqual(
        [l for l in self.stream_output.getvalue().splitlines() if l],
        [
            '@@@SEED_STEP LUCI Migration@@@',
            '@@@STEP_CURSOR LUCI Migration@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@$recipe_engine/runtime@{"is_experimental":'
              ' false, "is_luci": false}@@@',
            '@@@SET_BUILD_PROPERTY@luci_migration@{"status": "error", "error":'
              ' "The parameter passed to the from_stream() method should point'
              ' to a file."}@@@',
            '@@@STEP_CURSOR LUCI Migration@@@',
            '@@@STEP_CLOSED@@@',
            '@@@SEED_STEP LogDog Bootstrap@@@',
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@logdog_project@"project"@@@',
            '@@@SET_BUILD_PROPERTY@logdog_prefix@"prefix"@@@',
            ('@@@SET_BUILD_PROPERTY@log_location@'
             '"logdog://example.com/project/prefix/+/recipes/annotations"@@@'),
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_CLOSED@@@',
        ]
    )


class ConfigurationTest(unittest.TestCase):

  def setUp(self):
    self._orig_kitchen_config = remote_run._KITCHEN_CONFIG
    remote_run._KITCHEN_CONFIG = {
      'all': remote_run._ALL_BUILDERS,
      'whitelist': remote_run.KitchenConfig(
        builders=['foo', 'bar'],
        is_blacklist=False,
       ),
      'blacklist': remote_run.KitchenConfig(
        builders=['foo', 'bar'],
        is_blacklist=True,
       ),
    }

    self.buildbucket = {
      'build': {
        'bucket': 'master.tryserver.chromium.linux',
        'created_by': 'user:iannucci@chromium.org',
        'created_ts': '1494616236661800',
        'id': '8979775000984247248',
        'lease_key': '2065395720',
        'tags': [
          'builder:linux_chromium_rel_ng',
          'buildset:patch/rietveld/codereview.chromium.org/2852733003/1',
          'master:tryserver.chromium.linux',
          'user_agent:rietveld'
        ],
      },
    }

    self._orig_canary_masters = remote_run._CANARY_MASTERS
    remote_run._CANARY_MASTERS = set(('canary',))

  def tearDown(self):
    remote_run._KITCHEN_CONFIG_MASTERS = self._orig_kitchen_config
    remote_run._CANARY_MASTERS = self._orig_canary_masters

  def test_get_cipd_pins_stable(self):
    self.assertFalse(remote_run._get_is_canary('not.canary'))

  def test_get_cipd_pins_canary(self):
    self.assertTrue(remote_run._get_is_canary('canary'))

  def test_get_is_kitchen_unlisted(self):
    self.assertFalse(remote_run._get_is_kitchen('unlisted', 'buildername'))

  def test_get_is_kitchen_all(self):
    self.assertTrue(remote_run._get_is_kitchen('all', 'buildername'))

  def test_get_is_kitchen_whitelist(self):
    self.assertTrue(remote_run._get_is_kitchen('whitelist', 'foo'))
    self.assertTrue(remote_run._get_is_kitchen('whitelist', 'bar'))
    self.assertFalse(remote_run._get_is_kitchen('whitelist', 'baz'))

  def test_get_is_kitchen_blacklist(self):
    self.assertFalse(remote_run._get_is_kitchen('blacklist', 'foo'))
    self.assertFalse(remote_run._get_is_kitchen('blacklist', 'bar'))
    self.assertTrue(remote_run._get_is_kitchen('blacklist', 'baz'))

  def test_get_not_opt_in(self):
    self.buildbucket['build']['created_by'] = (
        'user:someone@chromium.org')
    props = {'buildbucket': json.dumps(self.buildbucket)}
    self.assertFalse(remote_run.get_is_opt_in(props))

  def test_get_is_opt_in(self):
    for user in remote_run._OPT_IN_USERS:
      self.buildbucket['build']['created_by'] = user
      props = {'buildbucket': json.dumps(self.buildbucket)}
      self.assertTrue(remote_run.get_is_opt_in(props))


if __name__ == '__main__':
  unittest.main()
