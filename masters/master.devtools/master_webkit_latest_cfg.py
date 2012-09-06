# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.factory import chromium_factory
from buildbot.scheduler import Scheduler


def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

scheduler_devtools = Scheduler(name='devtools_perf_scheduler',
    branch='trunk',
    treeStableTimer=60,
    builderNames = ['x64 Release',
                    'x64 Debug',
                    'x64 Release Clang'])

factory_release = linux().ChromiumWebkitLatestFactory(
    target='Release',
    tests=['devtools_perf'],
    options=['--build-tool=ninja',
             '--compiler=goma',
             'DumpRenderTree',
             'chrome',
             'pyautolib',
             'chromedriver'],
    factory_properties={
      'perf_id': 'chromium-devtools-perf-debug',
      'show_perf_results': True,
    }
  )

builder_release = {
  'name': 'x64 Release',
  'builddir': 'DevTools_Release',
  'factory': factory_release,
  'category': 'Linux'
}


factory_debug = linux().ChromiumWebkitLatestFactory(
    target='Debug',
    tests=['devtools_perf'],
    options=['--build-tool=ninja',
             '--compiler=goma',
             'DumpRenderTree',
             'chrome',
             'pyautolib',
             'chromedriver'],
    factory_properties={
      'perf_id': 'chromium-devtools-perf-debug',
      'show_perf_results': True,
    }
  )

builder_debug = {
  'name': 'x64 Debug',
  'builddir': 'DevTools_Debug',
  'factory': factory_debug,
  'category': 'Linux'
}

factory_release_clang = linux().ChromiumWebkitLatestFactory(
    target='Release',
    tests=['devtools_perf'],
    options=['--build-tool=ninja',
             '--compiler=goma-clang',
             'DumpRenderTree',
             'chrome',
             'pyautolib',
             'chromedriver'],
    factory_properties={
      'perf_id': 'chromium-devtools-perf-clang-release',
      'show_perf_results': True,
      'gclient_env': {
          'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
      }
    }
  )

builder_release_clang = {
  'name': 'x64 Release Clang',
  'builddir': 'DevTools_Release_Clang',
  'factory': factory_release_clang,
  'category': 'Linux'
}


def Update(config, active_master, c):
  c["builders"] = [builder_release,
                   builder_debug,
                   builder_release_clang]
  c["schedulers"] = [scheduler_devtools]
  return c
