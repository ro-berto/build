# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'pgo',
  'recipe_engine/platform',
]


def RunSteps(api):
  api.chromium.set_config('chromium', TARGET_PLATFORM='win')

  api.pgo.archive_profile_database('fake_revision')


def GenTests(api):
  yield (
      api.test('basic') +
      api.platform('win', 64)
  )

  yield (
      api.test('failure') +
      api.platform('win', 64) +
      api.step_data('archive profile database', retcode=1)
  )

