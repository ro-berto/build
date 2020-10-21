# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine import types

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec
from RECIPE_MODULES.depot_tools.gclient import CONFIG_CTX

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/bot_update',
    'recipe_engine/assertions',
    'recipe_engine/json',
    'recipe_engine/properties',
]


@CONFIG_CTX()
def override_foo(c):
  c.revisions['src/foo'] = 'HEAD'


def RunSteps(api):
  bot = api.chromium_tests.lookup_bot_metadata()
  api.chromium_tests.configure_build(bot.settings)
  update_step, _ = api.chromium_tests.prepare_checkout(bot.settings)
  properties = api.chromium_tests._get_trigger_properties(
      bot.builder_id, update_step)
  expected = types.thaw(api.properties['expected_trigger_properties'])
  for k, v in expected.iteritems():
    if k not in properties:  # pragma: no cover
      api.assertions.fail('Property {} not present, expected {!r}'.format(k, v))
    else:
      api.assertions.assertEqual(properties[k], v)


def GenTests(api):
  src_revision = api.bot_update.gen_revision('src')
  yield api.test(
      'overridden-dep',
      api.chromium.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          revision=src_revision),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-group': {
                  'fake-builder':
                      bot_spec.BotSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          gclient_apply_config=['override_foo'],
                      ),
                  'fake-tester':
                      bot_spec.BotSpec.create(
                          execution_mode=bot_spec.TEST,
                          chromium_config='chromium',
                          gclient_config='chromium',
                          gclient_apply_config=['override_foo'],
                          parent_buildername='fake-builder',
                      )
              },
          })),
      api.properties(
          expected_trigger_properties={
              '$build/chromium_tests': {
                  'fixed_revisions': {
                      'src': src_revision,
                      'src/foo': api.bot_update.gen_revision('src/foo'),
                  },
              },
          }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
