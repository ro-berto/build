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


def _normalize(x):
  if isinstance(x, (list, tuple)):
    return set(x)
  return x


BLACKLIST = [
    # TODO(gbeaty) This tester wants to run without LSan, its builder builds
    # with LSan
    ('chromium.memory', 'Linux ASan Tests (sandboxed)'),
]


def validate_tester_config(api, mastername, buildername, bot_config):
  if (mastername, buildername) in BLACKLIST:
    return

  parent_buildername = bot_config.get('parent_buildername')
  if parent_buildername == 'dummy':
    return

  parent_mastername = bot_config.get('parent_mastername', mastername)
  parent_bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(parent_mastername, parent_buildername)])

  for a in ('chromium_config',
            'chromium_apply_config',
            'chromium_config_kwargs',
            'android_config',
            'android_config_kwargs'):
    tester_value = _normalize(bot_config.get(a))
    builder_value = _normalize(parent_bot_config.get(a))
    assert tester_value == builder_value, (
        ('%s mismatch between tester and builder'
         '\n  tester %s:%s: %s'
         '\n  builder %s:%s: %s') % (
            a,
            mastername, buildername, tester_value,
            parent_mastername, parent_buildername, builder_value))


def RunSteps(api, mastername, buildername):
  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)])

  # For testers, check that various configs are equal to the builder's
  if bot_config.get('bot_type', 'builder_tester') == 'tester':
    validate_tester_config(api, mastername, buildername, bot_config)

  # Make sure that the configuration is valid
  api.chromium_tests.configure_build(bot_config)


def GenTests(api):
  for mastername, builders_dict in sorted(api.chromium_tests.builders.iteritems()):
    for buildername in sorted(builders_dict['builders']):
      yield (
          api.test(('%s-%s' % (mastername, buildername)).replace(' ', '_'))
          + api.properties(mastername=mastername, buildername=buildername)
          # We want any errors when creating the BotConfig to be surfaced
          # directly to the test rather than creating a failing step
          + api.chromium_tests.handle_bot_config_errors(False)
          + api.chromium_tests.platform(
              [{'mastername': mastername, 'buildername': buildername}])
          + api.post_process(post_process.DropExpectation))
