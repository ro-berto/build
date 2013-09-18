# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import re
import uuid

from slave import recipe_api

import utils

class AndroidApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(AndroidApi, self).__init__(**kwargs)

  def init_and_sync(self):
    internal = self.m.properties['internal']
    bot_id = self.m.properties['android_bot_id']
    target = self.m.properties.get('target', 'Debug')
    repo_name = self.m.properties['repo_name']
    repo_url = self.m.properties['repo_url']
    revision = self.m.properties.get('revision')
    gclient_custom_deps = self.m.properties.get('gclient_custom_deps')

    if internal:
      self.internal_dir = repo_name.split('/', 1)[-1]

    self.set_config(bot_id,
                    INTERNAL=internal,
                    REPO_NAME=repo_name,
                    REPO_URL=repo_url,
                    BUILD_CONFIG=target)

    # TODO(sivachandra): Move the setting of the gclient spec below to an
    # internal config extension when they are supported by the recipe system.
    spec = self.m.gclient.make_config('android_bare')
    spec.target_os = ['android']
    s = spec.solutions[0]
    s.name = repo_name
    s.url = repo_url
    s.custom_vars = self.c.custom_vars
    s.custom_deps = gclient_custom_deps or {}
    if revision:
      s.revision = revision
    else:
      s.revision = 'refs/remotes/origin/master'

    yield self.m.gclient.checkout(spec)

    # TODO(sivachandra): Manufacture gclient spec such that it contains "src"
    # solution + repo_name solution. Then checkout will be automatically
    # correctly set by gclient.checkout
    manual_checkout_path = self.m.path.slave_build('src')
    self.m.path.add_checkout(manual_checkout_path)
    self.m.path.choose_checkout(manual_checkout_path)

    self.build_internal_android = self.m.path.build_internal(
        'scripts', 'slave', 'android')

    for env_var, value in self.c.extra_env.items():
      if isinstance(value, list):
        self.c.extra_env[env_var] = self.m.path.checkout(*value)

    if internal:
      yield self.m.step(
          'Get AppManifestVars',
          [self.m.path.checkout(
               self.internal_dir, 'build', 'dump_app_manifest_vars.py'),
           '-b', self.m.properties['buildername'],
           '-v', self.m.path.checkout('chrome', 'VERSION'),
           self.m.json.output()]
      )

      app_manifest_vars = self.m.step_history.last_step().json.output
      gyp_defs = self.m.chromium.c.gyp_env.GYP_DEFINES
      gyp_defs['app_manifest_version_code'] = app_manifest_vars['version_code']
      gyp_defs['app_manifest_version_name'] = app_manifest_vars['version_name']
      gyp_defs['chrome_build_id'] = app_manifest_vars['build_id']

  def envsetup(self):
    envsetup_cmd = [self.m.path.checkout('build', 'android', 'envsetup.sh')]
    if self.c.target_arch:
      envsetup_cmd += ['--target-arch=%s' % self.c.target_arch]

    init_env = {}
    if self.m.properties.get('internal'):
      init_env = {
          'EXTRA_LANDMINES_SCRIPT': self.m.path.checkout(
              self.internal_dir, 'build', 'get_internal_landmines.py')
      }
    init_env.update(self.c.extra_env.as_jsonish())

    # TODO(sivachandra): make envsetup_cmd_to_json only output salient
    # differences in environment.
    cmd = ([self.m.path.checkout('build', 'env_dump.py'),
            self.m.json.output()] + envsetup_cmd)
    yield self.m.step('envsetup', cmd, env=init_env)

    self.env = self.m.step_history.last_step().json.output
    # TODO(sivachandra): Use os.pathsep equivalent instead of ':' when it
    # provided by one of the recipe modules.
    self.env['PATH'] += (self.build_internal_android + ':' +
                         self.env.get('PATH'))

  def clean_local_files(self):
    target = self.m.properties.get('target', 'Debug')
    debug_info_dumps = self.m.path.checkout('out', target, 'debug_info_dumps')
    test_logs = self.m.path.checkout('out', target, 'test_logs')
    return self.m.python.inline(
        'clean local files',
        """
          import shutil, sys, os
          shutil.rmtree(sys.argv[1], True)
          shutil.rmtree(sys.argv[2], True)
          for base, _dirs, files in os.walk(sys.argv[3]):
            for f in files:
              if f.endswith('.pyc'):
                os.remove(os.path.join(base, f))
        """,
        args=[debug_info_dumps, test_logs, self.m.path.checkout()],
    )

  def run_tree_truth(self, show_revisions=False):
    # TODO(sivachandra): The downstream ToT builder will require
    # 'Show Revisions' step.
    repos = ['src', 'src-internal']
    if self.c.REPO_NAME not in repos:
      repos.append(self.c.REPO_NAME)
    # TODO(sivachandra): Disable subannottations after cleaning up
    # tree_truth.sh.
    yield self.m.step('Tree Truth Steps',
                      [self.m.path.checkout('build', 'tree_truth.sh'), 
                       self.m.path.checkout()] + repos,
                      allow_subannottations=True)

  def runhooks(self):
    return self.m.gclient.runhooks(env=self.env)

  def compile(self, target='Debug'):
    return self.m.chromium.compile(env=self.env)

  def findbugs(self):
    cmd = [self.m.path.checkout('build', 'android', 'findbugs_diff.py')]
    if self.c.INTERNAL:
      cmd.extend(
          ['-b',
           self.m.path.checkout(self.internal_dir, 'bin', 'findbugs_filter'),
           '-o', 'com.google.android.apps.chrome.-,org.chromium.-'])
           
      return self.m.step('findbugs_internal', cmd, env=self.env)

  def checkdeps(self):
    return self.m.step(
      'checkdeps',
      [self.m.path.checkout('tools', 'checkdeps', 'checkdeps.py'),
       '--root=%s' % self.internal_dir],
      env=self.env)

  def lint(self):
    if self.c.INTERNAL:
      return self.m.step(
          'lint',
          [self.m.path.checkout(self.internal_dir, 'bin', 'lint.py')],
          env=self.env)
