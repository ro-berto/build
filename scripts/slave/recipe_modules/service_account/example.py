# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/platform',
    'recipe_engine/raw_io',
    'service_account',
]

"""Small example of using the service_account api."""

def RunSteps(api):
  _ = api.service_account.get_token('fake-account')


def GenTests(api):
  yield (api.test('service_account_win') +
         api.step_data('get access token',
                       stdout=api.raw_io.output('MockTokenValueThing')) +
         api.platform('win', 32))
  yield (api.test('service_account_linux') +
         api.step_data('get access token',
                       stdout=api.raw_io.output('MockTokenValueThing')) +
         api.platform('linux', 64))
  yield (api.test('service_account_no_authutil') +
         api.step_data('get access token',
                       retcode=1) +
         api.platform('linux', 64))
