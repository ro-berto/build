# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_gsutil',
    'recipe_engine/path',
]


def RunSteps(api):
  api.chromium_gsutil.download_latest_file(
      'https://example/url',
      'example_name',
      api.path['checkout'].join('destination'))


def GenTests(api):
  yield api.test('basic')
