# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Specifies how to launch the gatekeeper."""

from slave import recipe_util

def GetFactoryProperties(_build_properties):
  return {
      'script': recipe_util.Steps.build_path(
          'scripts', 'slave', 'gatekeeper_launch.py')}
