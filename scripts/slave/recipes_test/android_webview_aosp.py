# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test inputs for recipes/android_webview_aosp.py"""

def _common_test_data():
  return {
    'calculate trimmed deps': (0, {
        'blacklist': {
          'src/blacklist/project/1': None,
          'src/blacklist/project/2': None,
      }
    })
  }

def basic_test(api):
  return  {
    'build_properties': api.build_properties_scheduled(),
    'test_data': _common_test_data(),
  }


def uses_android_repo_test(api):
  return {
    'build_properties': api.build_properties_scheduled(),
    'test_data': _common_test_data(),
    'paths_to_mock' : [
        '[SLAVE_BUILD_ROOT]/android-src/.repo/repo/repo',
        '[SLAVE_BUILD_ROOT]/android-src',
    ],
  }

def does_delete_stale_chromium_test(api):
  return {
    'build_properties': api.build_properties_scheduled(),
    'test_data': _common_test_data(),
    'paths_to_mock' : [
        '[SLAVE_BUILD_ROOT]/android-src/external/chromium_org',
    ],
  }

def uses_goma_test(api):
  return {
    'build_properties': api.build_properties_scheduled(),
    'test_data': _common_test_data(),
    'paths_to_mock' : ['[BUILD_ROOT]/goma', ]
  }

def works_if_revision_not_present_test(api):
  return  {
    'build_properties': api.build_properties_generic(),
    'test_data': _common_test_data(),
  }
