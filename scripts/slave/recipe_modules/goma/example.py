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

  api.goma.build_with_goma(
      name='ninja',
      ninja_log_outdir=api.properties.get('ninja_log_outdir'),
      ninja_log_compiler=api.properties.get('ninja_log_compiler'),
      ninja_command=command,
      allow_build_without_goma=allow_build_without_goma,
      goma_env=env)


def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    properties = {
        'buildername': 'test_builder',
        'mastername': 'test_master',
        'slavename': 'test_slave',
        'clobber': '1',
        'build_command': ['ninja', '-j', '80', '-C', 'out/Release'],
        'ninja_log_outdir': 'out/Release',
        'ninja_log_compiler': 'goma',
        'build_data_dir': 'build_data_dir',
    }

    yield (api.test(platform) + api.platform.name(platform) +
           api.properties.generic(**properties))

    yield (api.test('%s_goma_disabled' % platform) +
           api.step_data('preprocess_for_goma.start_goma', retcode=1) +
           api.platform.name(platform) +
           api.properties(allow_build_without_goma=True) +
           api.properties.generic(**properties))
