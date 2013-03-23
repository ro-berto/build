# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Specifies how to launch the gatekeeper."""

def GetFactoryProperties(api, build_properties):
  return {
      'script':
          api.Steps.build_path('scripts', 'slave', 'gatekeeper_launch.py')
  }
