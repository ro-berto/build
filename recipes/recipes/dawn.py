# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/gsutil',
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
  'recipe_engine/time',
]

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'target_cpu': Property(default=None, kind=str),
  'debug': Property(default=False, kind=bool),
  'clang': Property(default=None, kind=bool),
}

DAWN_REPO = "https://dawn.googlesource.com/dawn"


def _checkout_steps(api):
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)

  with api.context(cwd=solution_path):
    # Checkout dawn and its dependencies (specified in DEPS) using gclient.
    api.gclient.set_config('dawn')
    api.gclient.c.got_revision_mapping['dawn'] = 'got_revision'
    # Standalone developer dawn builds want the dawn checkout in the same
    # directory the .gclient file is in.  Bots want it in a directory called
    # 'dawn'.  To make both cases work, the dawn DEPS file pulls deps and runs
    # hooks relative to the variable "root" which is set to . by default and
    # then to 'dawn' on bots here:
    api.gclient.c.solutions[0].custom_vars = {'dawn_root': 'dawn'}
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()


def _out_path(target_cpu, debug, clang, static):
  out_dir = 'debug' if debug else 'release'
  if clang:
    out_dir += '_clang'
  if target_cpu:
    out_dir += '_' + target_cpu
  if static:
    out_dir += '_static'
  else:
    out_dir += '_component'
  return out_dir


def _gn_gen_builds(api, target_cpu, debug, clang, out_dir, static, swiftshader):
  """calls 'gn gen'"""
  api.goma.ensure_goma()
  gn_bool = {True: 'true', False: 'false'}
  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.depot_tools.gn_py_path

  # Prepare the arguments to pass in.
  args = [
      'is_debug=%s' % gn_bool[debug],
      'is_component_build=%s' % gn_bool[not static],
      'use_goma=%s' % gn_bool[clang or clang is None],
      'dawn_use_swiftshader=%s' % gn_bool[swiftshader],
      'goma_dir="%s"' % api.goma.goma_dir,
  ]

  # We run the end2end tests with SwiftShader, but the D3D12 backend,
  # though it would run zero tests, crashes on Windows 7.
  # Disable it for now.
  if swiftshader:
    args.append('dawn_enable_d3d12=false')

  if clang is not None:
    args.append('is_clang=%s' % gn_bool[clang])

  if target_cpu:
    args.append('target_cpu="%s"' % target_cpu)

  with api.context(cwd=checkout):
    api.python('gn gen', gn_cmd,
               ['--root=' + str(checkout), 'gen', '//out/' + out_dir,
                '--args=' + ' '.join(args)])

def _get_compiler_name(api, clang):
  # Clang is used as the default compiler.
  if clang or clang is None:
    return 'clang'
  # The non-Clang compiler is OS-dependent.
  if api.platform.is_win:
    return 'msvc'
  return 'gcc'


def _build_steps(api, out_dir, clang, *targets):
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_cmd = [api.depot_tools.ninja_path, '-C', debug_path,
               '-j', api.goma.recommended_goma_jobs]
  ninja_cmd.extend(targets)

  api.goma.build_with_goma(
      name='compile with ninja',
      ninja_command=ninja_cmd,
      ninja_log_outdir=debug_path,
      ninja_log_compiler=_get_compiler_name(api, clang))

def _run_unittests(api, out_dir):
  test_path = api.path['checkout'].join('out', out_dir, 'dawn_unittests')
  api.step('Run the Dawn unittests', [test_path])
  api.step('Run the Dawn unittests with the wire', [test_path, '--use-wire'])


def _run_tint_generator_unittests(api, out_dir):
  test_path = api.path['checkout'].join('out', out_dir, 'dawn_unittests')
  api.step('Run the Dawn unittests',
           [test_path, '--enable-toggles=use_tint_generator'])


def _run_swiftshader_end2end_tests(api, out_dir):
  test_path = api.path['checkout'].join('out', out_dir, 'dawn_end2end_tests')
  api.step('Run the Dawn end2end tests with SwiftShader',
           [test_path, '--adapter-vendor-id=0x1AE0'])


def RunSteps(api, target_cpu, debug, clang):
  env = {}
  if api.platform.is_win:
    env['DEPOT_TOOLS_WIN_TOOLCHAIN_ROOT'] = (
    api.path['cache'].join('win_toolchain'))

  with api.context(env=env):
    _checkout_steps(api)
    out_dir_static = _out_path(target_cpu, debug, clang, static=True)
    out_dir_component = _out_path(target_cpu, debug, clang, static=False)
    with api.osx_sdk('mac'):
      # Static build all targets and run unittests
      _gn_gen_builds(
          api,
          target_cpu,
          debug,
          clang,
          out_dir_static,
          static=True,
          swiftshader=False)
      _build_steps(api, out_dir_static, clang)
      _run_unittests(api, out_dir_static)
      _run_tint_generator_unittests(api, out_dir_static)

      # Component build and run dawn_end2end_tests with SwiftShader
      # When using SwiftShader a component build should be used.
      # See anglebug.com/4396.
      _gn_gen_builds(
          api,
          target_cpu,
          debug,
          clang,
          out_dir_component,
          static=False,
          swiftshader=True)
      _build_steps(api, out_dir_component, clang, 'dawn_end2end_tests')
      _run_swiftshader_end2end_tests(api, out_dir_component)


def GenTests(api):
  yield api.test(
      'linux',
      api.platform('linux', 64),
      api.buildbucket.ci_build(
          project='dawn', builder='linux', git_repo=DAWN_REPO),
  )
  yield api.test(
      'linux_gcc',
      api.platform('linux', 64),
      api.properties(clang=False),
      api.buildbucket.ci_build(
          project='dawn', builder='linux', git_repo=DAWN_REPO),
  )
  yield api.test(
      'mac',
      api.platform('mac', 64),
      api.buildbucket.ci_build(
          project='dawn', builder='mac', git_repo=DAWN_REPO),
  )
  yield api.test(
      'win',
      api.platform('win', 64),
      api.buildbucket.ci_build(
          project='dawn', builder='win', git_repo=DAWN_REPO),
  )
  yield api.test(
      'win_clang',
      api.platform('win', 64),
      api.properties(clang=True),
      api.buildbucket.ci_build(
          project='dawn', builder='win', git_repo=DAWN_REPO),
  )
  yield api.test(
      'win_rel_msvc_x86',
      api.platform('win', 64),
      api.properties(clang=False, debug=False, target_cpu='x86'),
      api.buildbucket.ci_build(
          project='dawn', builder='win', git_repo=DAWN_REPO),
  )
