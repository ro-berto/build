# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'buildbucket',
    'puppet_service_account',
]


def RunSteps(api):
  service_account = api.puppet_service_account.get_key_path('username')

  api.buildbucket.get_build('9016911228971028736', service_account)


def GenTests(api):
  yield (
      api.test('basic') +
      api.buildbucket.simulated_buildbucket_output(None)
  )
