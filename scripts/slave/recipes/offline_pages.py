# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe for running Offline Pages integration tests."""

DEPS = [
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
  #TODO(bustamante): Add Offline Pages tests
  api.step('Placeholder Step', ['echo', 'Placeholder Step'])


def GenTests(api):
  yield (
      api.test('offline_pages_android') +
      api.properties.generic()
  )
