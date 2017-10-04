# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Small example of using the puppet_service_account api."""

DEPS = [
  'puppet_service_account',
  'recipe_engine/platform',
]


def RunSteps(api):
  access_token = api.puppet_service_account.get_access_token('fake-account')
  _ = access_token   # pass it somewhere, but be careful not to leak to logs


def GenTests(api):
  yield api.test('linux') + api.platform('linux', 64)
  yield api.test('win') + api.platform('win', 64)
