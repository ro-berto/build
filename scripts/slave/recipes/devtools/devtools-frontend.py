# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


def RunSteps(api):
  _configure(api)
  with _in_builder_cache_depot_on_path(api):
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()
    steps_n_scripts = [
      ('Compile Frontend', 'compile_frontend.py'),
      ('Lint', 'lint_javascript.py'),
      ('Run Tests', 'run_tests.py'),
    ]
    for step, script in steps_n_scripts:
      run_script(api, step, script)


def _configure(api):
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'devtools-frontend'
  soln.url = 'https://chromium.googlesource.com/devtools/devtools-frontend.git'
  soln.revision = api.properties.get('revision', 'HEAD')
  src_cfg.got_revision_mapping[soln.name] = 'got_revision'
  api.gclient.c = src_cfg


def run_script(api, step_name, script):
  with api.step.defer_results():
    sc_path = api.path['checkout'].join('scripts', script)
    api.python(step_name, sc_path)


@contextmanager
def _in_builder_cache_depot_on_path(api):
  cache_dir = api.path['builder_cache']
  depot_tools_path = api.path['checkout'].join('third_party', 'depot_tools')
  with api.context(cwd=cache_dir, env_prefixes={'PATH': [depot_tools_path]}):
    yield


def GenTests(api):
  yield api.test('basic', api.properties(path_config='kitchen'))
