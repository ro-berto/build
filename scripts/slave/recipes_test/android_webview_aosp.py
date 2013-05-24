# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test inputs for recipes/android_webview_aosp.py"""


def _common_factory_properties(**kwargs):
  ret = {
    'android_repo_url': 'https://android.googlesource.com/platform/manifest',
    'android_repo_branch': 'master',
  }
  ret.update(kwargs)
  return ret

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
    'factory_properties': _common_factory_properties(),
    'test_data': _common_test_data(),
  }

def with_ndk_pin_revision_test(api):
  return  {
    'factory_properties': _common_factory_properties(
      android_ndk_pin_revision='5049b437591600fb0d262e4215cee4226e63c6ce'
    ),
    'test_data': _common_test_data(),
  }

def with_resync_projects_test(api):
  return  {
    'factory_properties': _common_factory_properties(
      android_repo_resync_projects=['frameworks/base']
    ),
    'test_data': _common_test_data(),
  }

def uses_android_repo_test(api):
  return {
    'factory_properties': _common_factory_properties(),
    'test_data': _common_test_data(),
    'paths_to_mock' : [
        '[SLAVE_BUILD_ROOT]/android-src/.repo/repo/repo',
        '[SLAVE_BUILD_ROOT]/android-src',
    ],
  }

def does_delete_stale_chromium_test(api):
  return {
    'factory_properties': _common_factory_properties(),
    'test_data': _common_test_data(),
    'paths_to_mock' : [
        '[SLAVE_BUILD_ROOT]/android-src/external/chromium_org',
    ],
  }

def uses_goma_test(api):
  return {
    'factory_properties': _common_factory_properties(),
    'test_data': _common_test_data(),
    'paths_to_mock' : ['[BUILD_ROOT]/goma', ]
  }

