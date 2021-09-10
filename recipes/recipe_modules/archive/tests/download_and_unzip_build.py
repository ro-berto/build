# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'archive',
    'builder_group',
    'recipe_engine/path',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.archive.download_and_unzip_build(
      'extract build',
      target=api.path['checkout'].join('Release', 'out'),
      build_url=api.archive.legacy_download_url('bucket_name'),
      build_archive_url=api.properties.get('build_archive_url'),
      build_revision='example_sha',
  )


def GenTests(api):
  yield api.test(
      'basic',
      api.builder_group.for_current('test_group'),
      api.properties(
          parent_buildername='example_buildername',
          parent_buildnumber=1.0,
          buildnumber=123,
      ),
  )

  yield api.test(
      'build_archive_url',
      api.builder_group.for_current('test_group'),
      api.properties(
          parent_buildername='example_buildername',
          parentname='example_buildername',
          buildnumber=123,
          build_archive_url='https://example/url'),
  )
