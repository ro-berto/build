# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/osx_sdk',
    'goma',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

PROPERTIES = {
    'target_cpu': Property(default=None, kind=str),
    'debug': Property(default=False, kind=bool),
    'clang': Property(default=None, kind=bool),
}

TINT_REPO = "https://dawn.googlesource.com/tint"


def _checkout_steps(api):
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)

  with api.context(cwd=solution_path):
    # Checkout tint and its dependencies (specified in DEPS) using gclient.
    api.gclient.set_config('tint')
    api.gclient.c.got_revision_mapping['tint'] = 'got_revision'
    # Standalone developer tint builds want the tint checkout in the same
    # directory the .gclient file is in.  Bots want it in a directory called
    # 'tint'.  To make both cases work, the tint DEPS file pulls deps and runs
    # hooks relative to the variable "root" which is set to . by default and
    # then to 'tint' on bots here:
    api.gclient.c.solutions[0].custom_vars = {'tint_root': 'tint'}
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()


def _out_path(target_cpu, debug, clang):
  out_dir = 'debug' if debug else 'release'
  if clang:
    out_dir += '_clang'
  if target_cpu:
    out_dir += '_' + target_cpu
  return out_dir


def _get_compiler_name(api, clang):
  # Clang is used as the default compiler.
  if clang or clang is None:
    return 'clang'
  # The non-Clang compiler is OS-dependent.
  if api.platform.is_win:
    return 'msvc'
  return 'gcc'


def _use_goma(api, clang):
  return not api.platform.is_win or _get_compiler_name(api, clang) != 'msvc'


def _gn_gen_builds(api, target_cpu, debug, clang, out_dir):
  """calls 'gn gen'"""
  if _use_goma(api, clang):
    api.goma.ensure_goma()
  gn_bool = {True: 'true', False: 'false'}
  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.depot_tools.gn_py_path

  # Prepare the arguments to pass in.
  args = [
      'is_debug=%s' % gn_bool[debug],
      'tint_build_spv_reader=true',
      'tint_build_spv_writer=true',
      'tint_build_wgsl_reader=true',
      'tint_build_wgsl_writer=true',
      'tint_build_msl_writer=true',
      'tint_build_hlsl_writer=true',
  ]
  if _use_goma(api, clang):
    args.extend(['use_goma=true', 'goma_dir="%s"' % api.goma.goma_dir])

  if clang is not None:
    args.append('is_clang=%s' % gn_bool[clang])

  if target_cpu:
    args.append('target_cpu="%s"' % target_cpu)

  with api.context(cwd=checkout):
    api.python('gn gen', gn_cmd, [
        '--root=' + str(checkout), 'gen', '//out/' + out_dir, '--check',
        '--args=' + ' '.join(args)
    ])


def _build_steps(api, out_dir, clang, *targets):
  debug_path = api.path['checkout'].join('out', out_dir)

  ninja_cmd = [api.depot_tools.ninja_path, '-C', debug_path]
  if _use_goma(api, clang):
    ninja_cmd.extend(['-j', api.goma.recommended_goma_jobs])

  ninja_cmd.extend(targets)

  if _use_goma(api, clang):
    api.goma.build_with_goma(
        name='compile with ninja',
        ninja_command=ninja_cmd,
        ninja_log_outdir=debug_path,
        ninja_log_compiler=_get_compiler_name(api, clang))
  else:
    api.step('compile with ninja', ninja_cmd)


def _run_unittests(api, out_dir):
  test_path = api.path['checkout'].join('out', out_dir, 'tint_unittests')
  api.step('Run the Tint unittests', [test_path])


def RunSteps(api, target_cpu, debug, clang):
  env = {}
  if api.platform.is_win:
    env['DEPOT_TOOLS_WIN_TOOLCHAIN_ROOT'] = (
        api.path['cache'].join('win_toolchain'))

  with api.context(env=env):
    _checkout_steps(api)
    out_dir = _out_path(target_cpu, debug, clang)
    with api.osx_sdk('mac'):
      # Static build all targets and run unittests
      _gn_gen_builds(api, target_cpu, debug, clang, out_dir)
      _build_steps(api, out_dir, clang)
      _run_unittests(api, out_dir)


def GenTests(api):
  yield api.test(
      'linux',
      api.platform('linux', 64),
      api.buildbucket.ci_build(
          project='tint', builder='linux', git_repo=TINT_REPO) +
      api.post_process(post_process.MustRun, r'compile with ninja') +
      api.post_process(post_process.MustRun, r'Run the Tint unittests') +
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'linux_gcc',
      api.platform('linux', 64),
      api.properties(clang=False),
      api.buildbucket.ci_build(
          project='tint', builder='linux', git_repo=TINT_REPO) +
      api.post_process(post_process.MustRun, r'compile with ninja') +
      api.post_process(post_process.MustRun, r'Run the Tint unittests') +
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'mac',
      api.platform('mac', 64),
      api.buildbucket.ci_build(
          project='tint', builder='mac', git_repo=TINT_REPO) +
      api.post_process(post_process.MustRun, r'compile with ninja') +
      api.post_process(post_process.MustRun, r'Run the Tint unittests') +
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'win',
      api.platform('win', 64),
      api.buildbucket.ci_build(
          project='tint', builder='win', git_repo=TINT_REPO) +
      api.post_process(post_process.MustRun, r'compile with ninja') +
      api.post_process(post_process.MustRun, r'Run the Tint unittests') +
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'win_clang',
      api.platform('win', 64),
      api.properties(clang=True),
      api.buildbucket.ci_build(
          project='tint', builder='win', git_repo=TINT_REPO) +
      api.post_process(post_process.MustRun, r'compile with ninja') +
      api.post_process(post_process.MustRun, r'Run the Tint unittests') +
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'win_rel_msvc_x86',
      api.platform('win', 64),
      api.properties(clang=False, debug=False, target_cpu='x86'),
      api.buildbucket.ci_build(
          project='tint', builder='win', git_repo=TINT_REPO) +
      api.post_process(post_process.MustRun, r'compile with ninja') +
      api.post_process(post_process.MustRun, r'Run the Tint unittests') +
      api.post_process(post_process.DropExpectation),
  )
