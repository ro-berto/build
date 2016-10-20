# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
  'goma',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

def RunSteps(api):
  api.goma.ensure_goma()
  api.step('gn', ['gn', 'gen', 'out/Release',
                  '--args=use_goma=true goma_dir=%s' % api.goma.goma_dir])

  command = list(api.properties.get('build_command'))
  env = {}
  allow_build_without_goma = api.properties.get(
      'allow_build_without_goma', False)

  with api.goma.build_with_goma(
      ninja_log_outdir=api.properties.get('ninja_log_outdir'),
      ninja_log_compiler=api.properties.get('ninja_log_compiler'),
      ninja_log_command=command,
      allow_build_without_goma=allow_build_without_goma,
      env=env):
    if 'GOMA_DISABLED' in env:
      api.goma.remove_j_flag(command)
      api.step('ninja', command, env=env)
    else:
      # build something using goma.
      api.step('echo goma jobs',
               ['echo', str(api.goma.recommended_goma_jobs)])
      api.step('echo goma jobs second',
               ['echo', str(api.goma.recommended_goma_jobs)])
      api.step('ninja', command, env=env)

def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    properties = {
        'buildername': 'test_builder',
        'mastername': 'test_master',
        'slavename': 'test_slave',
        'clobber': '1',
        'build_command': ['ninja', '-C', 'out/Release', '-j', '500'],
        'ninja_log_outdir': 'out/Release',
        'ninja_log_compiler': 'goma',
        'build_data_dir': 'build_data_dir',
    }

    yield (api.test(platform) + api.platform.name(platform) +
           api.properties.generic(**properties))

    yield (api.test('%s_goma_disabled' % platform) +
           api.step_data('start_goma', retcode=1) +
           api.platform.name(platform) +
           api.properties(allow_build_without_goma=True) +
           api.properties.generic(**properties))
