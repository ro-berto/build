# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = ['android', 'properties', 'rietveld']

def GenSteps(api):
  droid = api.android
  droid.set_config('AOSP')
  yield droid.chromium_with_trimmed_deps()
  yield droid.lastchange_steps()

  if 'issue' in api.properties:
    yield api.rietveld.apply_issue(api.rietveld.calculate_issue_root())

  yield droid.repo_init_steps()
  yield droid.generate_local_manifest_step()
  yield droid.repo_sync_steps()

  yield droid.symlink_chromium_into_android_tree_step()
  yield droid.gyp_webview_step()

  # TODO(android): use api.chromium.compile for this
  yield droid.compile_step(
    build_tool='make-android',
    targets=['libwebviewchromium', 'android_webview_java'],
    use_goma=True)

def GenTests(api):
  def _common_placeholder_data():
    return {
      'calculate trimmed deps': {
        'json': {
          'output': {
            'blacklist': {
              'src/blacklist/project/1': None,
              'src/blacklist/project/2': None,
            }
          }
        }
      }
    }

  yield 'basic', {
    'build_properties': api.build_properties_scheduled(),
    'placeholder_data': _common_placeholder_data(),
  }

  yield 'uses_android_repo', {
    'build_properties': api.build_properties_scheduled(),
    'placeholder_data': _common_placeholder_data(),
    'mock' : {
      'path': {
        'exists': [
          '[SLAVE_BUILD_ROOT]/android-src/.repo/repo/repo',
          '[SLAVE_BUILD_ROOT]/android-src',
        ]
      }
    }
  }

  yield 'does_delete_stale_chromium', {
    'build_properties': api.build_properties_scheduled(),
    'placeholder_data': _common_placeholder_data(),
    'mock' : {
      'path': {
        'exists': [
          '[SLAVE_BUILD_ROOT]/android-src/external/chromium_org',
        ]
      }
    }
  }

  yield 'uses_goma_test', {
    'build_properties': api.build_properties_scheduled(),
    'placeholder_data': _common_placeholder_data(),
    'mock' : {
      'path': {
        'exists': [
          '[BUILD_ROOT]/goma'
        ]
      }
    }
  }

  yield 'works_if_revision_not_present', {
    'build_properties': api.build_properties_generic(),
    'placeholder_data': _common_placeholder_data(),
  }

  yield 'trybot', {
    'build_properties': api.build_properties_tryserver(),
    'placeholder_data': _common_placeholder_data(),
  }
