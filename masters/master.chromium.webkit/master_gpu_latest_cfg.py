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
    'builder': 'GPU Win7 (NVIDIA)',
    'perf_id': 'gpu-webkit-win7-nvidia',
    'factory_id': 'f_gpu_win_rel',
  },
  {
    'builder': 'GPU Win7 (dbg) (NVIDIA)',
    'factory_id': 'f_gpu_win_dbg',
  },
  {
    'builder': 'GPU Mac10.7',
    'perf_id': 'gpu-webkit-mac',
    'factory_id': 'f_gpu_mac_rel',
  },
  {
    'builder': 'GPU Mac10.7 (dbg)',
    'factory_id': 'f_gpu_mac_dbg',
  },
  {
    'builder': 'GPU Linux (NVIDIA)',
    'perf_id': 'gpu-webkit-linux-nvidia',
    'factory_id': 'f_gpu_linux_rel',
  },
  {
    'builder': 'GPU Linux (dbg) (NVIDIA)',
    'factory_id': 'f_gpu_linux_dbg',
  },
]

m_annotator = annotator_factory.AnnotatorFactory()

defaults['category'] = 'gpu'

for bot in gpu_bot_info:
  factory_properties = {
    'test_results_server': 'test-results.appspot.com',
    'generate_gtest_json': True,
    'build_config': 'Debug',
    'top_of_tree_blink': True
  }
  if 'perf_id' in bot:
    factory_properties['show_perf_results'] = True
    factory_properties['perf_id'] = bot['perf_id']
    factory_properties['build_config'] = 'Release'
  B(bot['builder'], bot['factory_id'], scheduler='global_scheduler')
  F(bot['factory_id'], m_annotator.BaseFactory('gpu', factory_properties))


def Update(_config, _active_master, c):
  return helper.Update(c)
