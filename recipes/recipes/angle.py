# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/osx_sdk',
    'goma',
    'depot_tools/gsutil',
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
    'uwp': Property(default=False, kind=bool),
}


def _IsGomaEnabled(clang):
  return clang is None or clang


def _CheckoutSteps(api):
  # Checkout angle and its dependencies (specified in DEPS) using gclient.
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)
  with api.context(cwd=solution_path):
    api.gclient.set_config('angle')
    api.gclient.c.got_revision_mapping['angle'] = 'got_revision'
    # Standalone developer angle builds want the angle checkout in the same
    # directory the .gclient file is in.  Bots want it in a directory called
    # 'angle'.  To make both cases work, the angle DEPS file pulls deps and runs
    # hooks relative to the variable "root" which is set to . by default and
    # then to 'angle' on bots here:
    api.gclient.c.solutions[0].custom_vars['angle_root'] = 'angle'
    # TODO (cnorthrop): Remove checkout_src_internal once ANGLE has been
    # migrated to use the new var checkout_angle_internal (crbug.com/1034542)
    api.gclient.c.solutions[0].custom_vars['checkout_src_internal'] = True
    api.gclient.c.solutions[0].custom_vars['checkout_angle_internal'] = True
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()


def _OutPath(target_cpu, debug, clang, uwp):
  out_dir = 'debug' if debug else 'release'
  if clang:
    out_dir += '_clang'
  if uwp:
    out_dir += '_uwp'
  if target_cpu:
    out_dir += '_' + target_cpu
  return out_dir


# _GNGenBuilds calls 'gn gen'.
def _GNGenBuilds(api, target_cpu, debug, clang, uwp, out_dir):
  gn_bool = {True: 'true', False: 'false'}

  # Prepare the arguments to pass in.
  args = [
      'build_angle_gles1_conform_tests=true',
      'build_angle_trace_perf_tests=true',
      'is_debug=%s' % gn_bool[debug],
      'is_component_build=false',
  ]

  if _IsGomaEnabled(clang):
    api.goma.ensure_goma()
    args.extend(['use_goma=true', 'goma_dir="%s"' % api.goma.goma_dir])
  else:
    # Goma implicitly sets symbol_level=1. Set explicitly here otherwise.
    args.extend(['symbol_level=1'])

  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.depot_tools.gn_py_path

  if clang is not None:
    args.append('is_clang=%s' % gn_bool[clang])

  if target_cpu:
    args.append('target_cpu="%s"' % target_cpu)

  if uwp:
    args.append('target_os="winuwp"')

  with api.context(cwd=checkout):
    api.python('gn gen', gn_cmd,
               ['--root=' + str(checkout), 'gen', '//out/' + out_dir,
                '--args=' + ' '.join(args), '--check'])


def _BuildSteps(api, out_dir, clang):
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_cmd = [api.depot_tools.ninja_path, '-C', debug_path]

  # TODO: Fix ANGLE linux-gcc build http://crbug.com/842146
  if 'linux-gcc' in api.buildbucket.builder_name:
    ninja_cmd.append('-n')

  if _IsGomaEnabled(clang):
    ninja_cmd.extend(['-j', api.goma.recommended_goma_jobs])
    api.goma.build_with_goma(
        name='compile with ninja',
        ninja_command=ninja_cmd,
        ninja_log_outdir=debug_path,
        ninja_log_compiler='clang')
  else:
    api.step('compile with ninja', ninja_cmd)


def RunSteps(api, target_cpu, debug, clang, uwp):

  env = {}
  if api.platform.is_win:
    env['DEPOT_TOOLS_WIN_TOOLCHAIN_ROOT'] = (
        api.path['cache'].join('win_toolchain'))

  with api.context(env=env):
    _CheckoutSteps(api)
    out_dir = _OutPath(target_cpu, debug, clang, uwp)
    with api.osx_sdk('mac'):
      _GNGenBuilds(api, target_cpu, debug, clang, uwp, out_dir)
      _BuildSteps(api, out_dir, clang)


def GenTests(api):

  def ci_build(builder):
    return api.buildbucket.ci_build(
        project='angle',
        builder=builder,
        build_number=1234,
        git_repo='https://chromium.googlesource.com/angle/angle.git')

  yield api.test(
      'linux',
      api.platform('linux', 64),
      ci_build(builder='linux'),
      api.builder_group.for_current('client.angle'),
  )
  yield api.test(
      'linux_gcc',
      api.platform('linux', 64),
      ci_build(builder='linux-gcc'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=False),
  )
  yield api.test(
      'win',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
  )
  yield api.test(
      'win_clang',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=True),
  )
  yield api.test(
      'win_rel_msvc_x86',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=False, debug=False, target_cpu='x86'),
  )
  yield api.test(
      'winuwp_dbg_msvc_x64',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=False, debug=True, uwp=True),
  )
