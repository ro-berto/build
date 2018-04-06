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
  'msvc': Property(default=False, kind=bool),
  'rel': Property(default=False, kind=bool),
}


def _CheckoutSteps(api):
  # Checkout angle and its dependencies (specified in DEPS) using gclient.
  api.gclient.set_config('angle')
  api.gclient.c.got_revision_mapping['angle'] = 'got_revision'
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()


def _OutPath(msvc, rel):
  out_dir = 'release' if rel else 'debug'
  if msvc:
    out_dir += '_msvc'
  return out_dir


# _GNGenBuilds calls 'gn gen'.
def _GNGenBuilds(api, target_cpu, msvc, rel, out_dir):
  api.goma.ensure_goma()
  gn_bool = {True: 'true', False: 'false'}
  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.depot_tools.gn_py_path

  # Prepare the arguments to pass in.
  args = [
      'is_debug=%s' % gn_bool[not rel],
      'is_component_build=false',
      'use_goma=true',
      'goma_dir="%s"' % api.goma.goma_dir,
  ]
  if api.platform.is_win:
    if msvc:
      args.append('is_clang=false')
  else:
    assert not msvc

  with api.context(cwd=checkout):
    api.python('gn gen', gn_cmd,
               ['--root=' + str(checkout), 'gen', '//out/' + out_dir,
                '--args=' + ' '.join(args)])


def _BuildSteps(api, msvc, out_dir):
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_cmd = ['ninja', '-C', debug_path,
               '-j', api.goma.recommended_goma_jobs]
  api.goma.build_with_goma(
      name='compile with ninja',
      ninja_command=ninja_cmd,
      ninja_log_outdir=debug_path,
      ninja_log_compiler='clang' if not msvc else 'unknown')


def RunSteps(api, target_cpu, msvc, rel):
  _CheckoutSteps(api)
  out_dir = _OutPath(msvc, rel)
  _GNGenBuilds(api, target_cpu, msvc, rel, out_dir)
  _BuildSteps(api, msvc, out_dir)


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
      api.test('win') +
      api.platform('win', 64) +
      api.properties(mastername='client.angle',
                     buildername='windows',
                     buildnumber='1234',
                     bot_id='test_slave')
  )
  yield (
      api.test('win_rel_msvc_x86') +
      api.platform('win', 64) +
      api.properties(msvc=True,
                     rel=True,
                     target_cpu='x86',
                     mastername='client.angle',
                     buildername='windows',
                     buildnumber='1234',
                     bot_id='test_slave')
  )
