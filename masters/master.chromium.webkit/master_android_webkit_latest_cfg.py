# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties

from master import master_config
from master import master_utils
from master.factory import remote_run_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

revision_getter = master_utils.ConditionalProperty(
    lambda build: build.getProperty('revision'),
    WithProperties('%(revision)s'),
    'master')

def m_remote_run_chromium_src(recipe, **kwargs):
  kwargs.setdefault('revision', revision_getter)
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/src.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      use_gitiles=True,
      **kwargs)


################################################################################
## Release
################################################################################

defaults['category'] = 'layout'

#
# Triggerable scheduler for the builder
#
T('android_rel_trigger')

#
# Android Rel Builder
#
B('Android Builder', 'f_android_rel', scheduler='global_scheduler')
F('f_android_rel', m_remote_run_chromium_src(
    'chromium', triggers=['android_rel_trigger']))

B('WebKit Android (Nexus4)', 'f_webkit_android_tests', None,
  'android_rel_trigger')
F('f_webkit_android_tests', m_remote_run_chromium_src('chromium'))

def Update(_config, _active_master, c):
  return helper.Update(c)
