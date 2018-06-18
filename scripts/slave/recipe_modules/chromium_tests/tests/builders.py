# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test to ensure the validity of the entries within BUILDERS.

Each entry in the BUILDERS dict will be checked to ensure
chromium_tests.configure_build can be called with a BotConfig for that builder
without error.
"""

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

DEPS = [
    'chromium_tests',
    'recipe_engine/platform',
    'recipe_engine/properties',
]

PROPERTIES = {
  'mastername': Property(
      kind=str, help='Name of the buildbot master to check'),
  'buildername': Property(
      kind=str, help='Name of the buildbot builder to check'),
}

BLACKLIST = [
  # TODO(crbug.com/853899) This builder spec is invalid, don't test it
  ('chromium.android', 'Android Cronet Builder Asan'),
]

def RunSteps(api, mastername, buildername):
  bot_config = (
      api.chromium_tests.create_bot_config_object(mastername, buildername))
  api.chromium_tests.configure_build(bot_config)

def GenTests(api):
  for mastername, builders_dict in api.chromium_tests.builders.iteritems():
    for buildername in builders_dict['builders']:
      if (mastername, buildername) in BLACKLIST:
        continue
      yield (
          api.test(('%s-%s' % (mastername, buildername)).replace(' ', '_'))
          + api.properties(mastername=mastername, buildername=buildername)
          # We want any errors when creating the BotConfig to be surfaced
          # directly to the test rather than creating a failing step
          + api.chromium_tests.handle_bot_config_errors(False)
          + api.chromium_tests.platform(
              [{'mastername': mastername, 'buildername': buildername}])
          + api.post_process(post_process.DropExpectation))
