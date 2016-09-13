# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'goma',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

def RunSteps(api):
  api.goma.ensure_goma()

  with api.goma.build_with_goma(ninja_log_outdir=api.properties.get('ninja_log_outdir'),
                                ninja_log_compiler=api.properties.get('ninja_log_compiler'),
                                ninja_log_command=api.properties.get('ninja_log_command'),
                                env={}):
    # build something using goma.
    api.step('echo goma jobs',
             ['echo', str(api.goma.recommended_goma_jobs)])
    api.step('echo goma jobs second',
             ['echo', str(api.goma.recommended_goma_jobs)])

def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    properties = {
        'buildername': 'test_builder',
        'mastername': 'test_master',
        'slavename': 'test_slave',
        'clobber': '1',
    }

    yield (api.test(platform) + api.platform.name(platform) +
           api.properties.generic(**properties))

    properties.update({
        'build_data_dir': 'build_data_dir',
        'ninja_log_outdir': 'build_data_dir',
        'ninja_log_compiler': 'goma',
        'ninja_log_command': ['ninja', '-j', '500'],
    })

    yield (api.test('%s_upload_logs' % platform) + api.platform.name(platform) +
           api.properties.generic(**properties))
