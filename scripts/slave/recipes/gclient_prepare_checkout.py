# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Steps to execute before a gclient sync on the slave."""

def GetFactoryProperties(api, _factory_properties, build_properties):
  steps = api.Steps(build_properties)
  return {
    'steps': [
      steps.step('revert',
                 [
                     api.python(),
                     api.build_path('scripts', 'slave',
                                    'gclient_safe_revert.py'),
                     api.slave_build_path(),
                     api.depot_tools_path('gclient.py'),
                 ]),
    ]
  }
