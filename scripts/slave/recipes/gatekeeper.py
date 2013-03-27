# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Specifies how to launch the gatekeeper."""

def GetFactoryProperties(api, _factory_properties, build_properties):
  steps = api.Steps(build_properties)
  return {
    'steps': [
      steps.step('gatekeeper_launch',
                 api.build_path('scripts', 'slave', 'gatekeeper_launch.py'))
    ]
  }
