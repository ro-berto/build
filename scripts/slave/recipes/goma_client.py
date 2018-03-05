# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]


def RunSteps(api):
  # 1. Checkout the source
  src_cfg = api.gclient.make_config()
  src_cfg.got_revision_mapping['client'] = 'got_revision'
  soln = src_cfg.solutions.add()
  soln.name = 'client'
  soln.url = 'https://chromium.googlesource.com/infra/goma/client'
  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout(clobber=False, gerrit_no_reset=True)
  api.gclient.runhooks()

  # 2. Build
  build_out_dir = api.path['checkout'].join('out')
  build_target = 'Release'
  build_dir = build_out_dir.join(build_target)

  # 2-1. gn
  gn_args = [
      'is_debug=false',
      'cpu_arch="x64"',
      'dcheck_always_on=true',
      'use_link_time_optimization=false'
  ]
  api.python(
      name='gn',
      script=api.depot_tools.gn_py_path,
      args=[
          '--root=%s' % str(api.path['checkout']),
          'gen',
          build_dir,
          '--args=%s' % ' '.join(gn_args)])

  # 2-2. ninja
  api.step('build', [api.depot_tools.ninja_path, '-C', build_dir])

  # 3. Run test
  with api.context():
    api.python(
        name='tests',
        script=api.path['checkout'].join('build', 'run_unittest.py'),
        args=['--build-dir', build_out_dir,
              '--target', build_target, '--non-stop'])


def GenTests(api):
  yield (api.test('goma_client_linux_rel') +
         api.platform('linux', 64) +
         api.properties(
             buildername='linux_rel',
             mastername='client.goma',
             revision='f3cdb946812584bc1789076599929fac4dc5da2b'))
