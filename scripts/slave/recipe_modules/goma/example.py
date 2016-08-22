# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'goma',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
]

def RunSteps(api):
  api.goma.ensure_goma()
  api.goma.start(env={})
  # build something using goma.
  api.goma.stop(
      ninja_log_outdir=api.properties.get('ninja_log_outdir'),
      ninja_log_compiler=api.properties.get('ninja_log_compiler'),
      ninja_log_command=api.properties.get('ninja_log_command'),
      ninja_log_exit_status=api.properties.get('ninja_log_exit_status'),
  )


def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    yield api.test(platform) + api.platform.name(platform)

    properties = {
        'build_data_dir': 'build_data_dir',
        'ninja_log_outdir': 'build_data_dir',
        'ninja_log_compiler': 'goma',
        'ninja_log_command': 'ninja -j 500',
        'ninja_log_exit_status': 0,
    }

    yield (api.test('%s_upload_logs' % platform) + api.platform.name(platform) +
           api.properties.generic(**properties))
