# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'path',
  'properties',
  'python',
]


def _CheckoutSteps(api, buildername):
  # Checkout catapult and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('catapult')
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()


def GenSteps(api):
  buildername = api.properties.get('buildername')
  _CheckoutSteps(api, buildername)
  api.python('Util Tests',
             api.path['checkout'].join('base', 'util', 'run_tests.py'))


def GenTests(api):
  # Run GenSteps with default input
  yield (api.test('basic') +
         api.properties(mastername='master.client.catapult',
                        buildername='windows',
                        slavename='windows_slave'))
