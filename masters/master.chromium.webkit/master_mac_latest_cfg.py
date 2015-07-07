# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

def mac():
  return chromium_factory.ChromiumFactory('src/out', 'darwin')

defaults['category'] = 'nonlayout'

################################################################################
## Debug
################################################################################

# Triggerable scheduler for testers
T('mac_builder_dbg_trigger')

#
# Mac Dbg Builder
#
B('Mac Builder (dbg)', 'f_mac_builder_dbg', scheduler='global_scheduler')
F('f_mac_builder_dbg', mac().ChromiumFactory(
    target='Debug',
    # Build 'all' instead of 'chromium_builder_tests' so that archiving works.
    # TODO: Define a new build target that is archive-friendly?
    options=['--build-tool=ninja', '--compiler=goma-clang', 'all'],
    factory_properties={
        'trigger': 'mac_builder_dbg_trigger',
        'gclient_env': {
            'GYP_DEFINES': 'fastbuild=1',
            'GYP_GENERATORS': 'ninja',
        },
        'archive_build': True,
        'blink_config': 'blink',
        'build_name': 'Mac',
        'gs_bucket': 'gs://chromium-webkit-snapshots',
        'gs_acl': 'public-read',
    }))

B('Mac10.6 Tests', 'f_mac_tester_10_06_dbg',
  scheduler='mac_builder_dbg_trigger')
F('f_mac_tester_10_06_dbg', mac().ChromiumFactory(
    tests=[
      'browser_tests',
      'cc_unittests',
      'content_browsertests',
      'interactive_ui_tests',
      'telemetry_unittests',
      'unit',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'blink_config': 'blink',
    }))


B('Mac10.8 Tests', 'f_mac_tester_10_08_dbg',
  scheduler='mac_builder_dbg_trigger')
F('f_mac_tester_10_08_dbg', mac().ChromiumFactory(
    tests=[
      'browser_tests',
      'content_browsertests',
      'interactive_ui_tests',
      'telemetry_unittests',
      'unit',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
