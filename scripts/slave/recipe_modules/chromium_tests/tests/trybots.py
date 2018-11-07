# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test to ensure the validity of the entries within TRYBOTS.

Each entry in the TRYBOTS dict will be checked to ensure
chromium_tests.trybot_steps can be called with the mastername and buildername
properties set for the entry.
"""

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

DEPS = [
    'chromium_tests',
    'recipe_engine/properties',
    'recipe_engine/step',
]

def RunSteps(api):
  api.chromium_tests.trybot_steps()
  api.step('Success', ['echo', 'Success!'])

def GenTests(api):
  for mastername, builders_dict in api.chromium_tests.trybots.iteritems():
    for buildername in builders_dict['builders']:
      yield (
          api.test(('%s-%s' % (mastername, buildername)).replace(' ', '_'))
          + api.properties.generic(
              mastername=mastername, buildername=buildername)
          # We want any errors when creating the BotConfig to be surfaced
          # directly to the test rather than creating a failing step
          + api.chromium_tests.handle_bot_config_errors(False)
          + api.post_process(post_process.DropExpectation))
  yield (
      api.test('tryserver.chromium.linux-linux-coverage-rel')
      + api.properties.generic(mastername='tryserver.chromium.linux',
                               buildername='linux-coverage-rel')
      # We want any errors when creating the BotConfig to be surfaced
      # directly to the test rather than creating a failing step
      + api.chromium_tests.handle_bot_config_errors(False)
      + api.post_process(post_process.DropExpectation))
