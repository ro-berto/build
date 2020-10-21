# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Packages Androidx libraries as CIPD packages."""

from recipe_engine import post_process
from PB.recipe_engine import result as result_pb
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipes.build.android import sdk_packager

import math

DEPS = [
    'chromium',
    'chromium_checkout',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
    'recipe_engine/time',
]

PROPERTIES = sdk_packager.InputProperties


def RunSteps(api, properties):
  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.chromium_checkout.ensure_checkout()

  androidx_dir = api.path['checkout'].join('third_party', 'androidx')
  androidx_libs_dir = androidx_dir.join('libs')

  api.file.ensure_directory('ensure libs dir exists', androidx_libs_dir)
  api.file.rmcontents('delete libs dir contents', androidx_libs_dir)

  if api.file.listdir('check libs empty', androidx_libs_dir):
    return result_pb.RawResult(
        status=common_pb.INFRA_FAILURE,
        summary_markdown='Unable to delete androidx libs directory.')

  fetch_all_cmd = androidx_dir.join('fetch_all_androidx.py')
  api.step('fetch_all', [fetch_all_cmd])
  api.path.mock_add_paths(androidx_dir.join('cipd.yaml'))

  yaml_path = androidx_dir.join('cipd.yaml')
  version = 'cr-' + str(math.floor(api.time.time() / 60 / 60 / 24))
  api.cipd.create_from_yaml(yaml_path, tags={'version': version})


def GenTests(api):
  androidx_dir = api.path['checkout'].join('third_party', 'androidx')
  androidx_sample_lib = androidx_dir.join('libs', 'androidx_dino')

  yield api.test(
      'basic',
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='android-androidx-packager'),
      api.path.exists(
          androidx_dir.join('fetch_all_androidx.py'),
          androidx_sample_lib.join('README.chromium')),
      api.post_process(post_process.MustRun, 'fetch_all'),
      api.post_process(post_process.MustRun, 'create cipd.yaml'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'directory-deletion-fails',
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='android-androidx-packager'),
      api.path.exists(
          androidx_dir.join('fetch_all_androidx.py'),
          androidx_sample_lib.join('README.chromium')),
      api.override_step_data('check libs empty',
                             api.file.listdir(['androidx_dino/cipd.yaml'])),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )
