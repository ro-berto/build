# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from recipe_engine import post_process
import json

DEPS = [
    'builder_group',
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/git',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'perf_dashboard',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
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
    clean_out_dir(api)
    api.chromium.run_gn(use_goma=True)
    compilation_result = api.chromium.compile(use_goma_module=True)
    if compilation_result.status != common_pb.SUCCESS:
      return compilation_result

    run_unit_tests(api)
    publish_coverage_points(api)

    if is_debug_builder(api):
      return

    run_lint_check(api)
    run_localization_check(api)
    run_e2e(api)

    if can_run_experimental_teps(api):
      # Place here any unstable steps that you want to be performed on
      # builders with property run_experimental_steps == True
      run_interactions(api)


def builder_config(api):
  return api.properties.get('builder_config', 'Release')


def is_debug_builder(api):
  return builder_config(api) == 'Debug'


def is_clobber(api):
  return api.properties.get('clobber', False)


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
  config_name = builder_config(api)
  build_cfg = api.chromium.make_config(BUILD_CONFIG=config_name)
  build_cfg.build_config_fs = config_name
  build_cfg.compile_py.use_autoninja = True
  build_cfg.compile_py.compiler = 'goma'
  api.chromium.c = build_cfg


def run_script(api, step_name, script, args=None):
  with api.step.defer_results():
    sc_path = api.path['checkout'].join('scripts', 'test', script)
    args = args or []
    api.python(step_name, sc_path, args=args)


def run_node_script(api, step_name, script, args=None):
  with api.context(cwd=api.path['checkout']):
    sc_path = api.path.join('third_party', 'node', 'node.py')
    node_args = ['--output', api.path.join('scripts', 'test', script)]
    node_args.extend(args or [])
    api.python(step_name, sc_path, args=node_args)


def run_unit_tests(api):
  run_script(api, 'Unit Tests', 'run_unittests.py', [
      '--target=' +  builder_config(api),
      '--coverage',
    ])


def run_lint_check(api):
  run_node_script(api, 'Lint Check with ESLint', 'run_lint_check_js.js')


def run_localization_check(api):
  run_script(api, 'Localization Check', 'run_localization_check.py')


def run_e2e(api):
  run_script(api, 'E2E tests', 'run_test_suite.py',
             ['--target=' +  builder_config(api), '--test-suite=e2e'])


def run_interactions(api):
  run_script(api, 'Interactions', 'run_test_suite.py',
             ['--target=' +  builder_config(api), '--test-suite=interactions'])


# TODO(liviurau): remove this temp hack after devtools refactorings that
# involve .gitignore are done
def _git_clean(api):
  with api.context(cwd=api.path['checkout']):
    api.git('clean', '-xf', '--', 'front_end')


def clean_out_dir(api):
  if is_clobber(api):
    dir_to_clean = 'Release'
  elif is_debug_builder(api):
    dir_to_clean = 'Debug'
  else:
    return
  path_to_clean = api.path['checkout'].join('out', dir_to_clean)
  api.file.rmtree('clean outdir', path_to_clean)


@contextmanager
def _in_builder_cache(api):
  cache_dir = api.path['cache'].join('builder')
  with api.context(cwd=cache_dir):
    yield


@contextmanager
def _depot_on_path(api):
  depot_tools_path = api.path['checkout'].join('third_party')
  with api.context(env_prefixes={'PATH': [depot_tools_path]}):
    yield


def can_run_experimental_teps(api):
  return api.properties.get('run_experimental_steps', False)


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

def publish_coverage_points(api):
  if api.tryserver.is_tryserver or not is_debug_builder(api):
    return

  dimensions = ["lines", "statements", "functions", "branches"]

  report_file = api.path['checkout'].join('karma-coverage',
                                          'coverage-summary.json')
  if not api.path.exists(report_file):
    return

  summary = api.file.read_json(
      'Coverage summary', report_file, test_data=test_cov_data())
  totals = summary['total']
  api.step.active_result.presentation.step_text = "".join([
      "\n%s: %s%%" % (dim.capitalize(), totals[dim]['pct'])
      for dim in dimensions
  ])

  points = [_point(api, dim, summary['total']) for dim in dimensions]
  #TODO(liviurau) find another way arroud 400 error "Invalid ID (revision) 1055;
  #compared to previous ID 0, it was larger or smaller by too much."
  api.perf_dashboard.add_point(points, halt_on_failure=False)


def _point(api, dimension, totals):
  p = api.perf_dashboard.get_skeleton_point(
      '/'.join(['devtools.infra', 'coverage', dimension]),
      api.buildbucket.build.number,
      totals[dimension]['pct'],
  )
  p['supplemental_columns'] = {
      'a_default_rev': 'r_devtools_git',
      'r_devtools_git': api.bot_update.last_returned_properties['got_revision'],
  }
  return p


def GenTests(api):
  git_repo = 'https://chromium.googlesource.com/devtools/devtools-frontend'

  def ci_build(builder):
    return api.buildbucket.ci_build(
        project='devtools', builder=builder, git_repo=git_repo)

  def try_build(builder, **kwargs):
    return api.buildbucket.try_build(
        project='devtools',
        builder=builder,
        git_repo=git_repo,
        change_number=91827,
        patch_set=1,
        **kwargs)

  yield api.test(
      'basic try',
      api.builder_group.for_current('tryserver.devtools-frontend'),
      try_build(builder='linux'),
  )

  yield api.test(
      'basic no cov',
      api.builder_group.for_current('devtools-frontend'),
      ci_build(builder='linux'),
  )

  yield api.test(
      'experimental',
      api.builder_group.for_current('tryserver.devtools-frontend'),
      try_build(builder='linux'),
      api.properties(run_experimental_steps=True),
  )

  yield api.test(
      'compile failure',
      api.builder_group.for_current('devtools-frontend'),
      ci_build(builder='linux'),
      api.step_data('compile', retcode=1),
      api.post_process(post_process.StatusFailure),
  )

  yield api.test(
      'basic win',
      api.builder_group.for_current('devtools-frontend'),
      ci_build(builder='win'),
      api.platform('win', 64),
  )

  yield api.test(
      'basic debug',
      api.builder_group.for_current('tryserver.devtools-frontend'),
      ci_build(builder='linux'),
      api.properties(builder_config='Debug'),
  )

  yield api.test(
      'debug cov',
      api.builder_group.for_current('tryserver.devtools-frontend'),
      ci_build(builder='linux'),
      api.properties(builder_config='Debug'),
      api.path.exists(api.path['checkout'].join(
          'karma-coverage',
          'coverage-summary.json',
      )),
  )

  yield api.test(
      'full build',
      api.builder_group.for_current('tryserver.devtools-frontend'),
      ci_build(builder='linux'),
      api.properties(clobber=True),
      api.post_process(post_process.MustRun, 'clean outdir'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
