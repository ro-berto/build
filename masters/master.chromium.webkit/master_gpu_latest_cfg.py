# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import annotator_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

# TODO(kbr): it would be better if this waterfall were refactored so
# that we could access the slaves_list here.
gpu_bot_info = [
  {
    'builder': 'GPU Win Builder',
    'factory_id': 'f_gpu_win_builder_rel',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Release',
  },
  {
    'builder': 'GPU Win Builder (dbg)',
    'factory_id': 'f_gpu_win_builder_dbg',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Debug',
  },
  {
    'builder': 'GPU Win7 (NVIDIA)',
    'factory_id': 'f_gpu_win_rel',
    'recipe': 'gpu/build_and_test',
    'build_config': 'Release',
    'perf_id': 'gpu-webkit-win7-nvidia',
  },
  {
    'builder': 'GPU Win7 (dbg) (NVIDIA)',
    'factory_id': 'f_gpu_win_dbg',
    'recipe': 'gpu/build_and_test',
    'build_config': 'Debug',
  },
  {
    'builder': 'GPU Mac Builder',
    'factory_id': 'f_gpu_mac_builder_rel',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Release',
  },
  {
    'builder': 'GPU Mac Builder (dbg)',
    'factory_id': 'f_gpu_mac_builder_dbg',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Debug',
  },
  {
    'builder': 'GPU Mac10.7',
    'factory_id': 'f_gpu_mac_rel',
    'recipe': 'gpu/build_and_test',
    'build_config': 'Release',
    'perf_id': 'gpu-webkit-mac',
  },
  {
    'builder': 'GPU Mac10.7 (dbg)',
    'factory_id': 'f_gpu_mac_dbg',
    'recipe': 'gpu/build_and_test',
    'build_config': 'Debug',
  },
  {
    'builder': 'GPU Linux Builder',
    'factory_id': 'f_gpu_linux_builder_rel',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Release',
  },
  {
    'builder': 'GPU Linux Builder (dbg)',
    'factory_id': 'f_gpu_linux_builder_dbg',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Debug',
  },
  {
    'builder': 'GPU Linux (NVIDIA)',
    'factory_id': 'f_gpu_linux_rel',
    'recipe': 'gpu/build_and_test',
    'build_config': 'Release',
    'perf_id': 'gpu-webkit-linux-nvidia',
  },
  {
    'builder': 'GPU Linux (dbg) (NVIDIA)',
    'factory_id': 'f_gpu_linux_dbg',
    'recipe': 'gpu/build_and_test',
    'build_config': 'Debug',
  },
]

m_annotator = annotator_factory.AnnotatorFactory()

defaults['category'] = 'gpu'

for bot in gpu_bot_info:
  factory_properties = {
    'test_results_server': 'test-results.appspot.com',
    'generate_gtest_json': True,
    'build_config': bot['build_config'],
    'top_of_tree_blink': True
  }
  if 'perf_id' in bot:
    factory_properties['show_perf_results'] = True
    factory_properties['perf_id'] = bot['perf_id']
  B(bot['builder'], bot['factory_id'], scheduler='global_scheduler')
  F(bot['factory_id'], m_annotator.BaseFactory(
      bot['recipe'],
      factory_properties))


def Update(_config, _active_master, c):
  return helper.Update(c)
