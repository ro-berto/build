# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from recipe_engine.post_process import (DropExpectation, StatusFailure)
import json

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/git',
    'depot_tools/gclient',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

STEPS_N_SCRIPTS = [
  ('Unit Tests', 'run_unittests.py'),
  ('Type Check', 'run_type_check.py'),
  ('Lint Check', 'run_lint_check.py'),
  ('Localization Check', 'run_localization_check.py'),
]

REPO_URL = 'https://chromium.googlesource.com/devtools/devtools-frontend.git'

def RunSteps(api):
  _configure(api)

  with _in_builder_cache(api):
    api.bot_update.ensure_checkout()
    _git_clean(api)
    api.gclient.runhooks()

  with _depot_on_path(api):
    api.chromium.ensure_goma()
    api.chromium.run_gn(use_goma=True)
    compilation_result = api.chromium.compile(use_goma_module=True)
    if compilation_result.status != common_pb.SUCCESS:
      return compilation_result
    for step, script in STEPS_N_SCRIPTS:
      run_script(api, step, script)

    report_file = api.path['checkout'].join('karma-coverage',
                                            'coverage-summary.json')
    if api.path.exists(report_file):
      summary = api.file.read_json(
          'Coverage summary', report_file, test_data=test_cov_data())

      s = api.step.active_result
      s.presentation.step_text = "Statement coverage %s%%" % summary['total'][
          'statements']['pct']


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
    sc_path = api.path['checkout'].join('scripts', 'test', script)
    api.python(step_name, sc_path)


# TODO(liviurau): remove this temp hack after devtools refactorings that
# involve .gitignore are done
def _git_clean(api):
  with api.context(cwd=api.path['checkout']):
    api.git('clean', '-xf', '--', 'front_end')


@contextmanager
def _in_builder_cache(api):
  cache_dir = api.path['builder_cache']
  with api.context(cwd=cache_dir):
    yield


@contextmanager
def _depot_on_path(api):
  depot_tools_path = api.path['checkout'].join('third_party')
  with api.context(env_prefixes={'PATH': [depot_tools_path]}):
    yield


def test_cov_data():
  return {
      "total": {
          "lines": {
              "pct": 11.11
          },
          "statements": {
              "pct": 11.12
          },
          "functions": {
              "pct": 11.13
          },
          "branches": {
              "pct": 11.14
          },
      }
  }


def GenTests(api):
  yield api.test(
      'basic no cov',
      api.properties(path_config='generic'),
  )
  yield api.test(
      'basic with cov',
      api.properties(path_config='generic'),
      api.path.exists(api.path['checkout'].join('karma-coverage',
                                                'coverage-summary.json')),
  )
  yield api.test(
      'compile failure',
      api.properties(path_config='generic'),
      api.step_data('compile', retcode=1),
      api.post_process(StatusFailure),
  )
