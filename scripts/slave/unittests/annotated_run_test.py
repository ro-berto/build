#!/usr/bin/env python

# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests that the tools/build annotated_run wrapper actually runs."""

import collections
import json
import logging
import os
import StringIO
import subprocess
import sys
import tempfile
import unittest

import test_env  # pylint: disable=W0403,W0611

import mock
from common import annotator
from common import env
from slave import annotated_run
from slave import logdog_bootstrap
from slave import robust_tempdir
from slave import update_scripts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MockOptions = collections.namedtuple('MockOptions',
    ('dry_run', 'logdog_disable'))


class AnnotatedRunTest(unittest.TestCase):
  def test_example(self):
    build_properties = {
      'mastername': 'tryserver.chromium.linux',
      'buildername': 'builder',
      'slavename': 'bot42-m1',
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

  @mock.patch('slave.update_scripts._run_command')
  @mock.patch('slave.annotated_run._run_command')
  @mock.patch('slave.annotated_run.main')
  @mock.patch('sys.platform', return_value='win')
  @mock.patch('tempfile.mkstemp', side_effect=Exception('failure'))
  def test_update_scripts_must_run(self, _tempfile_mkstemp, _sys_platform,
                                   main, annotated_run_command,
                                   update_scripts_run_command):
    update_scripts._run_command.return_value = (0, "")
    annotated_run._run_command.return_value = (0, "")
    annotated_run.main.side_effect = Exception('Test error!')
    annotated_run.shell_main(['annotated_run.py', 'foo'])

    gclient_path = os.path.join(env.Build, os.pardir, 'depot_tools',
                                'gclient.bat')
    annotated_run_command.assert_has_calls([
        mock.call([sys.executable, 'annotated_run.py', 'foo']),
        ])
    update_scripts_run_command.assert_has_calls([
        mock.call([gclient_path, 'sync',
                   '--force', '--delete_unversioned_trees',
                   '--break_repo_locks', '--verbose', '--jobs=2'],
                  cwd=env.Build),
        ])
    main.assert_not_called()


class AnnotatedRunExecTest(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR+1)

    self.maxDiff = None
    self._patchers = []
    map(self._patch, (
        mock.patch('slave.annotated_run._run_command'),
        mock.patch('slave.annotated_run._build_dir'),
        mock.patch('slave.annotated_run._builder_dir'),
        mock.patch('slave.annotated_run._get_engine_flags'),
        mock.patch('os.path.exists'),
        ))

    # Mock build and builder directories.
    annotated_run._build_dir.return_value = '/home/user/builder/build'
    annotated_run._builder_dir.return_value = '/home/user/builder'

    self.rt = robust_tempdir.RobustTempdir(prefix='annotated_run_test')
    self.stream_output = StringIO.StringIO()
    self.stream = annotator.StructuredAnnotationStream(
        stream=self.stream_output)
    self.basedir = self.rt.tempdir()
    self.tdir = self.rt.tempdir()
    self.opts = MockOptions(
        dry_run=False,
        logdog_disable=False)
    self.properties = {
      'slavename': 'bot42-m1',
      'recipe': 'example/recipe',
      'mastername': 'tryserver.chromium.linux',
      'buildername': 'builder',
    }
    self.rpy_path = os.path.join(env.Build, 'scripts', 'slave', 'recipes.py')
    self.recipe_args = [
        sys.executable, '-u', self.rpy_path, '--verbose', 'run',
        '--workdir=/home/user/builder/build',
        '--properties-file=%s' % (self._tp('recipe_properties.json'),),
        '--output-result-json', self._tp('recipe_result.json'),
        'example/recipe']

    # Use public recipes.py path.
    os.path.exists.return_value = False

    # Swap out testing _ENGINE_FLAGS.
    annotated_run._get_engine_flags.return_value = {}

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

  def _assertRecipeProperties(self, value):
    # Double-translate "value", since JSON converts strings to unicode.
    value = json.loads(json.dumps(value))
    with open(self._tp('recipe_properties.json')) as fd:
      self.assertEqual(json.load(fd), value)

  def _writeRecipeResult(self, v):
    with open(self._tp('recipe_result.json'), 'w') as fd:
      json.dump(v, fd)

  def test_exec_successful(self):
    annotated_run._run_command.return_value = (0, '')
    self._writeRecipeResult({})

    rv = annotated_run._exec_recipe(
        self.rt, self.opts, self.stream, self.basedir, self.tdir,
        self.properties)
    self.assertEqual(rv, 0)
    self._assertRecipeProperties(self.properties)

    annotated_run._run_command.assert_called_once_with(self.recipe_args,
                                                       dry_run=False)

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  @mock.patch('slave.logdog_bootstrap.BootstrapState.get_result')
  def test_exec_with_logdog_bootstrap(self, bs_result, bootstrap):
    bootstrap.return_value = logdog_bootstrap.BootstrapState(
        ['logdog_bootstrap'] + self.recipe_args, '/path/to/result.json',
        'project', 'prefix')
    bootstrap.return_value.get_result.return_value = 13
    annotated_run._run_command.return_value = (13, '')
    self._writeRecipeResult({})

    rv = annotated_run._exec_recipe(
        self.rt, self.opts, self.stream, self.basedir, self.tdir,
        self.properties)

    self.assertEqual(rv, 13)
    annotated_run._run_command.assert_called_once_with(
        ['logdog_bootstrap'] + self.recipe_args, dry_run=False)
    self._assertRecipeProperties(self.properties)

    self.assertEqual(
        [l for l in self.stream_output.getvalue().splitlines() if l],
        [
            '@@@SEED_STEP LogDog Bootstrap@@@',
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_STARTED@@@',
            '@@@SET_BUILD_PROPERTY@logdog_project@"project"@@@',
            '@@@SET_BUILD_PROPERTY@logdog_prefix@"prefix"@@@',
            '@@@STEP_CURSOR LogDog Bootstrap@@@',
            '@@@STEP_CLOSED@@@',
        ]
    )

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  def test_exec_with_logdog_bootstrap_fail_raises(self, bootstrap):
    bootstrap.side_effect = logdog_bootstrap.BootstrapError('Bootstrap failed')

    with self.assertRaises(logdog_bootstrap.BootstrapError):
      _ = annotated_run._exec_recipe(
          self.rt, self.opts, self.stream, self.basedir, self.tdir,
          self.properties)

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  def test_exec_with_result_proto(self, bootstrap):
    bootstrap.side_effect = logdog_bootstrap.NotBootstrapped()
    annotated_run._get_engine_flags.return_value = {
        'use_result_proto': True,
    }
    annotated_run._run_command.return_value = (13, '')
    self._writeRecipeResult({})

    rv = annotated_run._exec_recipe(
        self.rt, self.opts, self.stream, self.basedir, self.tdir,
        self.properties)
    self.assertEqual(rv, 13)

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  def test_exec_with_result_proto_fail(self, bootstrap):
    bootstrap.side_effect = logdog_bootstrap.NotBootstrapped()
    annotated_run._get_engine_flags.return_value = {
        'use_result_proto': True,
    }
    annotated_run._run_command.return_value = (13, '')
    self._writeRecipeResult({
        'failure': {},
    })

    rv = annotated_run._exec_recipe(
        self.rt, self.opts, self.stream, self.basedir, self.tdir,
        self.properties)
    self.assertEqual(rv, 255)

  @mock.patch('slave.logdog_bootstrap.bootstrap')
  def test_exec_with_result_proto_step_fail(self, bootstrap):
    bootstrap.side_effect = logdog_bootstrap.NotBootstrapped()
    annotated_run._get_engine_flags.return_value = {
        'use_result_proto': True,
    }
    annotated_run._run_command.return_value = (13, '')
    self._writeRecipeResult({
        'failure': {
            'step_failure': True,
        },
    })

    rv = annotated_run._exec_recipe(
        self.rt, self.opts, self.stream, self.basedir, self.tdir,
        self.properties)
    self.assertEqual(rv, 13)


if __name__ == '__main__':
  unittest.main()
