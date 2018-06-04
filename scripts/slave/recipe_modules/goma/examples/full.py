# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re

DEPS = [
  'goma',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

def RunSteps(api):
  goma_local = api.properties.get('local_run_goma_recipe', False)
  env = {}

  if goma_local:
    goma_dir = '/home/goma/goma'
    api.python.inline('check gomacc file',"""
    import os.path
    if os.path.exists(os.path.join('%s','gomacc')):
      exit(0)
    exit(1)
    """ % goma_dir)
    api.goma.set_goma_dir_for_local_test(goma_dir)

  api.goma.ensure_goma(api.properties.get('canary', False))

  api.step('gn', ['gn', 'gen', 'out/Release',
                  '--args=use_goma=true goma_dir=%s' % api.goma.goma_dir])

  command = list(api.properties.get('build_command'))
  if api.properties.get('custom_tmp_dir'):
    env['GOMA_TMP_DIR'] = api.properties.get('custom_tmp_dir')

  command += ['-j', str(api.goma.jobs)]

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
      'build_command': ['ninja', '-C', 'out/Release'],
      'ninja_log_outdir': 'out/Release',
      'ninja_log_compiler': 'goma',
      'build_data_dir': 'build_data_dir',
      'buildbucket': json.dumps({'build': {'id': 1}}),
  }

  for platform in ('linux', 'win', 'mac'):
    yield (api.test(platform) + api.platform.name(platform) +
           api.properties.generic(**properties))

  yield (api.test('linux_custom_jobs') + api.platform.name('linux') +
           api.properties.generic(**properties) + api.goma(jobs=80))

  yield (api.test('linux_compile_failed') + api.platform.name('linux') +
         api.step_data('ninja', retcode=1) +
         api.properties.generic(**properties))

  yield (api.test('linux_start_goma_failed') + api.platform.name('linux') +
         api.step_data('preprocess_for_goma.start_goma', retcode=1) +
         api.properties.generic(**properties))

  yield (api.test('linux_stop_goma_failed') + api.platform.name('linux') +
         api.step_data('postprocess_for_goma.stop_goma', retcode=1) +
         api.properties.generic(**properties))

  yield (api.test('linux_set_custome_tmp_dir') + api.platform.name('linux') +
         api.properties(custom_tmp_dir='/tmp/goma_goma_module') +
         api.properties.generic(**properties))

  yield (api.test('linux_invalid_goma_jsonstatus') + api.platform.name('linux') +
         api.step_data('postprocess_for_goma.goma_jsonstatus',
                       api.json.output(data=None)) +
         api.properties.generic(**properties))

  yield (api.test('linux_local_run_goma_recipe') + api.platform.name('linux') +
         api.properties(local_run_goma_recipe=True) +
         api.properties.generic(**properties))

  yield (api.test('win_goma_canary') + api.platform.name('win') +
         api.properties(canary=True) +
         api.properties.generic(**properties))
