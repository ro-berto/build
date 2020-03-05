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

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import bot_spec
from RECIPE_MODULES.build.chromium_tests import builders

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/platform',
    'recipe_engine/properties',
]

def _normalize(x):
  if isinstance(x, (list, tuple)):
    return set(x)
  return x


VALIDATORS = {
    ('chromium.memory', 'Linux ASan Tests (sandboxed)',
     'chromium_apply_config'):
    lambda tester_value, builder_value: (
        builder_value - tester_value == set(['lsan']),
        'chromium_apply_config for tester should be '
        "the same as its builder with 'lsan' removed"),
}


def validate_tester_config(api, mastername, buildername, bot_config):
  # Some builders are 'dummy' builders. They don't actually run, but are created
  # for configuration reasons. Don't validate these builders.
  if 'dummy' in buildername:
    return  # pragma: no cover
  parent_buildername = bot_config.parent_buildername

  parent_mastername = bot_config.parent_mastername or mastername
  parent_bot_config = api.chromium_tests.create_bot_config_object([
      chromium.BuilderId.create_for_master(parent_mastername,
                                           parent_buildername)
  ])

  for a in ('chromium_config', 'chromium_apply_config',
            'chromium_config_kwargs', 'android_config'):
    tester_value = _normalize(getattr(bot_config, a))
    builder_value = _normalize(getattr(parent_bot_config, a))

    validator = VALIDATORS.get(
        (mastername, buildername, a),
        lambda tester_value, builder_value: (
            tester_value == builder_value,
            '%s mismatch between tester and builder' % a))

    valid, description = validator(tester_value, builder_value)
    assert valid, description + (
        '\n  tester %s:%s: %s'
        '\n  builder %s:%s: %s') % (
            mastername, buildername, tester_value,
            parent_mastername, parent_buildername, builder_value)


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  bot_config = api.chromium_tests.create_bot_config_object([builder_id])

  # For testers, check that various configs are equal to the builder's
  if bot_config.bot_type == bot_spec.TESTER:
    validate_tester_config(api, builder_id.master, builder_id.builder,
                           bot_config)

  # Make sure that the configuration is valid
  api.chromium_tests.configure_build(bot_config)


def GenTests(api):
  for builder_id in sorted(builders.BUILDERS):
    mastername = builder_id.master
    buildername = builder_id.builder
    yield api.test(
        ('%s-%s' % (mastername, buildername)).replace(' ', '_'),
        api.properties(mastername=mastername, buildername=buildername),
        # We want any errors when creating the BotConfig to be surfaced
        # directly to the test rather than creating a failing step
        api.chromium_tests.handle_bot_config_errors(False),
        api.chromium_tests.platform([{
            'mastername': mastername,
            'buildername': buildername
        }]),
        api.post_process(post_process.DropExpectation),
    )
