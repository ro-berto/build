# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = 'gpu'

#
# Linux Rel tests
#

B('GPU Linux (NVIDIA)', 'f_gpu_linux_rel', scheduler='global_scheduler')
F('f_gpu_linux_rel', linux().ChromiumFactory(
    target='Release',
    tests=[
        'gl_tests',
        'gpu_frame_rate',
        'gpu_latency',
        'gpu_throughput',
        'gpu_tests',
        'gpu_content_tests',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'chromium_gpu_builder',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'perf_id': 'gpu-webkit-linux-nvidia',
        'show_perf_results': True,
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'blink_config': 'blink',
    }))

################################################################################
## Debug
################################################################################

B('GPU Linux (dbg) (NVIDIA)', 'f_gpu_linux_dbg', scheduler='global_scheduler')
F('f_gpu_linux_dbg', linux().ChromiumFactory(
    target='Debug',
    tests=[
        'gl_tests',
        'gpu_tests',
        'gpu_content_tests',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'chromium_gpu_debug_builder'
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'blink_config': 'blink',
    }))


def Update(_config, _active_master, c):
  return helper.Update(c)
