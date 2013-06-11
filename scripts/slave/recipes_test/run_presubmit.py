# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test inputs for recipes/run_presubmit.py"""

def blink_bare_test(api):
  return {
    'factory_properties': {'repo_name': 'blink_bare'},
    'build_properties': api.build_properties_tryserver(
      root='src/third_party/WebKit'
    ),
  }

def blink_test(api):
  return {
    'factory_properties': {'repo_name': 'blink'},
    'build_properties': api.build_properties_tryserver(
      root='src/third_party/WebKit'
    ),
  }

def tools_build_test(api):
  return {
    'factory_properties': {'repo_name': 'tools_build'},
    'build_properties': api.build_properties_tryserver(),
  }

def chromium_test(api):
  return {
    'factory_properties': {'repo_name': 'chromium'},
    'build_properties': api.build_properties_tryserver(),
  }
