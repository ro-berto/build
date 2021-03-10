# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from recipe_engine import post_process
from recipe_engine.recipe_api import Property

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

PROPERTIES = {
    'builder_config':
        Property(
            kind=str,
            help='Configuration name for the builder (Debug/Release)',
            default='Release'),
    'is_official_build':
        Property(
            kind=bool,
            help='Turn the is_official_build gn flag on (default off)',
            default=False),
    'clobber':
        Property(
            kind=bool,
            help='Should the builder clean up the out/ folder before building',
            default=False),
    'e2e_env':
        Property(
            kind=dict,
            help='A set of environment variables to be used when running e2e'
            'stress tests. If set we only compile and run e2e tests.'
            'Example vars:  the subset of tests to be run, number of'
            'iterations, etc.',
            default=None),
    # TODO: remove e2e_env property once the runner gets updated
    'runner_args':
        Property(
            kind=str,
            help='Parameters to be passed down to the test runner for running'
            ' stess e2e tests. If set we only compile and run e2e tests.',
            default=None),
}



REPO_URL = 'https://chromium.googlesource.com/devtools/devtools-frontend.git'


def RunSteps(api, builder_config, is_official_build, clobber, e2e_env,
             runner_args):
  _configure(api, builder_config, is_official_build)

  with _in_builder_cache(api):
    api.bot_update.ensure_checkout()
    _git_clean(api)
    api.gclient.runhooks()

  with _depot_on_path(api):
    api.chromium.ensure_goma()
    clean_out_dir(api, builder_config, clobber)
    api.chromium.run_gn(use_goma=True)
    compilation_result = api.chromium.compile(use_goma_module=True)
    if compilation_result.status != common_pb.SUCCESS:
      return compilation_result

    # TODO(liviurau): move this logic in a separate recipe
    # to maybe even add bysection later on
    builder_name = api.buildbucket.builder_name
    if (e2e_env or runner_args) and builder_name.startswith("e2e"):
      # run only e2e stress tests
      # TODO(liviurau): use parameters rahter than ENV vars
      if e2e_env:
        with api.context(env=e2e_env):
          run_e2e(api, builder_config)
      else:
        run_e2e(api, builder_config, runner_args.split())
      return

    run_unit_tests(api, builder_config)
    publish_coverage_points(api, builder_config)

    if _is_debug(builder_config):
      return

    run_lint_check(api)

    # TODO(liviurau): temporary removal of localization check. We need to think
    # about making this configurable on the builder side to choose/add steps
    # and configure script arguments 
    #run_localization_check(api)
    
    run_e2e(api, builder_config)
    run_interactions(api, builder_config)

    if can_run_experimental_teps(api):
      # Place here any unstable steps that you want to be performed on
      # builders with property run_experimental_steps == True
      pass

def _is_debug(builder_config):
  return builder_config == 'Debug'


def _configure(api, builder_config, is_official_build):
  _configure_source(api)
  _configure_build(api, builder_config, is_official_build)


def _configure_source(api):
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'devtools-frontend'
  soln.url = REPO_URL
  soln.revision = api.properties.get('revision', 'HEAD')
  src_cfg.got_revision_mapping[soln.name] = 'got_revision'
  api.gclient.c = src_cfg


def _configure_build(api, builder_config, is_official_build):
  build_cfg = api.chromium.make_config(BUILD_CONFIG=builder_config)
  build_cfg.build_config_fs = builder_config
  build_cfg.compile_py.compiler = 'goma'
  if is_official_build:
    build_cfg.gn_args.append('is_official_build=true')
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


def run_unit_tests(api, builder_config):
  run_script(api, 'Unit Tests', 'run_unittests.py', [
      '--target=' +  builder_config,
      '--coverage',
    ])


def run_lint_check(api):
  run_node_script(api, 'Lint Check with ESLint', 'run_lint_check_js.js')


def run_localization_check(api): # pragma: no cover
  run_script(api, 'Localization Check', 'run_localization_check.py')


def run_e2e(api, builder_config, args=None):
  run_script(api, 'E2E tests', 'run_test_suite.py',
             ['--target=' + builder_config, '--test-suite=e2e'] + (args or []))


def run_interactions(api, builder_config):
  run_script(api, 'Interactions', 'run_test_suite.py',
             ['--target=' +  builder_config, '--test-suite=interactions'])


# TODO(liviurau): remove this temp hack after devtools refactorings that
# involve .gitignore are done
def _git_clean(api):
  with api.context(cwd=api.path['checkout']):
    api.git('clean', '-xf', '--', 'front_end')


def clean_out_dir(api, builder_config, clobber):
  if clobber:
    dir_to_clean = 'Release'
  elif _is_debug(builder_config):
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

def publish_coverage_points(api, builder_config):
  if api.tryserver.is_tryserver or not _is_debug(builder_config):
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

  yield api.test(
      'official build',
      api.builder_group.for_current('tryserver.devtools-frontend'),
      ci_build(builder='linux'),
      api.properties(is_official_build=True),
      api.post_process(post_process.Filter('gn'))
  )

  yield api.test(
      'e2e stress test',
      api.builder_group.for_current('tryserver.devtools-frontend'),
      try_build(builder='e2e_stressor_linux'),
      api.properties(e2e_env={
          'ITERATIONS': '100',
          'SUITE': 'flaky suite'
      }),
      api.post_process(post_process.DoesNotRun, 'Unit Tests'),
      api.post_process(post_process.Filter('E2E tests')),
  )

  yield api.test(
      'e2e stress test with parameters',
      api.builder_group.for_current('tryserver.devtools-frontend'),
      try_build(builder='e2e_stressor_linux'),
      api.properties(runner_args="--ITERATIONS=100 --SUITE=flaky/suite"),
      api.post_process(post_process.DoesNotRun, 'Unit Tests'),
      api.post_process(post_process.Filter('E2E tests')),
  )
