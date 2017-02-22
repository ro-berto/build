# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
  'goma',
  'recipe_engine/path',
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

  api.goma.build_with_goma(
      name='ninja',
      ninja_log_outdir=api.properties.get('ninja_log_outdir'),
      ninja_log_compiler=api.properties.get('ninja_log_compiler'),
      ninja_command=command,
      goma_env=env)


def GenTests(api):
  properties = {
      'buildername': 'test_builder',
      'mastername': 'test_master',
      'bot_id': 'test_slave',
      'clobber': '1',
      'build_command': ['ninja', '-j', '80', '-C', 'out/Release'],
      'ninja_log_outdir': 'out/Release',
      'ninja_log_compiler': 'goma',
      'build_data_dir': 'build_data_dir',
  }

  for platform in ('linux', 'win', 'mac'):
    yield (api.test(platform) + api.platform.name(platform) +
           api.properties.generic(**properties))

  yield (api.test('linux_compile_failed') + api.platform.name('linux') +
         api.step_data('ninja', retcode=1) +
         api.properties.generic(**properties))

  yield (api.test('old_cache_dir') + api.properties.generic(**properties) +
         api.path.exists(api.path['cache'].join('cipd', 'goma')))

  yield (api.test('old_cache_dir_fail') + api.properties.generic(**properties) +
         api.path.exists(api.path['cache'].join('cipd', 'goma')) +
         api.step_data('ensure_goma.clean old goma dir', retcode=1))
