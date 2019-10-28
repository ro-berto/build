# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from recipe_engine.post_process import (DropExpectation, StatusFailure)

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

STEPS_N_SCRIPTS = [
  ('Compile Frontend', 'compile_frontend.py'),
  ('Lint', 'lint_javascript.py'),
  ('Run Tests', 'run_tests.py'),
]

REPO_URL = 'https://chromium.googlesource.com/devtools/devtools-frontend.git'


def RunSteps(api):
  _configure(api)
  with _in_builder_cache_depot_on_path(api):
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()
    api.chromium.ensure_goma()
    api.chromium.run_gn(use_goma=True)
    compilation_result = api.chromium.compile(use_goma_module=True)
    if compilation_result.status != common_pb.SUCCESS:
      return compilation_result
    for step, script in STEPS_N_SCRIPTS:
      run_script(api, step, script)


def _configure(api):
  _configure_source(api)
  _configure_build(api)


def _configure_source(api):
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'devtools-frontend'
  soln.url = REPO_URL
  soln.revision = api.properties.get('revision', 'HEAD')
  src_cfg.got_revision_mapping[soln.name] = 'got_revision'
  api.gclient.c = src_cfg


def _configure_build(api):
  build_cfg = api.chromium.make_config()
  build_cfg.build_config_fs = 'Release'
  build_cfg.compile_py.use_autoninja = True
  build_cfg.compile_py.compiler = 'goma'
  api.chromium.c = build_cfg


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
  yield (api.test('compile failure', api.properties(path_config='kitchen')) +
         api.step_data('compile', retcode=1) + api.post_process(StatusFailure))
