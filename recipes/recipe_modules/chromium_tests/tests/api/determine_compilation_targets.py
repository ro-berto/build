# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  builder_id, bot_config = api.chromium_tests.lookup_builder()
  api.chromium_tests.configure_build(bot_config)
  _, build_config = api.chromium_tests.prepare_checkout(bot_config)
  affected_files = api.properties['affected_files']
  api.chromium_tests._determine_compilation_targets(builder_id, bot_config,
                                                    affected_files,
                                                    build_config)


def GenTests(api):

  def affected_spec_file():
    return sum([
        api.chromium.try_build(
            builder_group='fake-try-group', builder='fake-try-builder'),
        api.properties(affected_files=['testing/buildbot/fake-group.json']),
        api.chromium_tests.builders(
            bot_db.BotDatabase.create({
                'fake-group': {
                    'fake-builder':
                        bot_spec.BotSpec.create(
                            chromium_config='chromium',
                            gclient_config='chromium',
                        ),
                },
            })),
        api.chromium_tests.trybots(
            try_spec.TryDatabase.create({
                'fake-try-group': {
                    'fake-try-builder':
                        try_spec.TrySpec.create_for_single_mirror(
                            'fake-group', 'fake-builder'),
                },
            })),
    ], api.empty_test_data())

  for platform in ('linux', 'win'):
    yield api.test(
        'affected spec file {}'.format(platform),
        api.platform(platform, 64),
        affected_spec_file(),
        api.post_check(lambda check, steps: check(steps['analyze'].cmd == [])),
        api.post_process(post_process.DropExpectation),
    )
