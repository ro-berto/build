# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'goma',
  'depot_tools/gsutil',
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
    # hooks relative to the variable "root" which is set to . by default and then
    # to 'angle' on bots here:
    api.gclient.c.solutions[0].custom_vars = {'angle_root': 'angle'}
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()

def _OutPath(target_cpu, debug, clang):
  out_dir = 'debug' if debug else 'release'
  if clang:
    out_dir += '_clang'
  if target_cpu:
    out_dir += '_' + target_cpu
  return out_dir


# _GNGenBuilds calls 'gn gen'.
def _GNGenBuilds(api, target_cpu, debug, clang, out_dir):
  api.goma.ensure_goma()
  gn_bool = {True: 'true', False: 'false'}
  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.depot_tools.gn_py_path

  # Prepare the arguments to pass in.
  args = [
      'is_debug=%s' % gn_bool[debug],
      'is_component_build=false',
      'use_goma=true',
      'goma_dir="%s"' % api.goma.goma_dir,
  ]
  if clang is not None:
    args.append('is_clang=%s' % gn_bool[clang])

  if target_cpu:
    args.append('target_cpu="%s"' % target_cpu)

  with api.context(cwd=checkout):
    api.python('gn gen', gn_cmd,
               ['--root=' + str(checkout), 'gen', '//out/' + out_dir,
                '--args=' + ' '.join(args)])


def _GetCompilerName(api, clang):
  # Clang is used as the default compiler.
  if clang or clang is None:
    return 'clang'
  # The non-Clang compiler is OS-dependent.
  if api.platform.is_win:
    return 'msvc'
  else:
    return 'gcc'

def _BuildSteps(api, out_dir, clang):
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_cmd = [api.depot_tools.ninja_path, '-C', debug_path,
               '-j', api.goma.recommended_goma_jobs]
  api.goma.build_with_goma(
      name='compile with ninja',
      ninja_command=ninja_cmd,
      ninja_log_outdir=debug_path,
      ninja_log_compiler=_GetCompilerName(api, clang))


def RunSteps(api, target_cpu, debug, clang):
  _CheckoutSteps(api)
  out_dir = _OutPath(target_cpu, debug, clang)
  _GNGenBuilds(api, target_cpu, debug, clang, out_dir)
  _BuildSteps(api, out_dir, clang)


def GenTests(api):
  yield (
      api.test('linux') +
      api.platform('linux', 64) +
      api.properties(mastername='client.angle',
                     buildername='linux',
                     buildnumber='1234',
                     bot_id='test_slave')
  )
  yield (
      api.test('linux_gcc') +
      api.platform('linux', 64) +
      api.properties(clang=False,
                     mastername='client.angle',
                     buildername='linux',
                     buildnumber='1234',
                     bot_id='test_slave')
  )
  yield (
      api.test('win') +
      api.platform('win', 64) +
      api.properties(mastername='client.angle',
                     buildername='windows',
                     buildnumber='1234',
                     bot_id='test_slave')
  )
  yield (
      api.test('win_clang') +
      api.platform('win', 64) +
      api.properties(clang=True,
                     mastername='client.angle',
                     buildername='windows',
                     buildnumber='1234',
                     bot_id='test_slave')
  )
  yield (
      api.test('win_rel_msvc_x86') +
      api.platform('win', 64) +
      api.properties(clang=False,
                     debug=False,
                     target_cpu='x86',
                     mastername='client.angle',
                     buildername='windows',
                     buildnumber='1234',
                     bot_id='test_slave')
  )
