# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  api.chromium_tests.configure_build(builder_config)
  _, targets_config = api.chromium_tests.prepare_checkout(builder_config)
  affected_files = api.properties['affected_files']
  api.chromium_tests.determine_compilation_targets(builder_id, builder_config,
                                                   affected_files,
                                                   targets_config)


def GenTests(api):

  def affected_spec_file():
    return sum([
        api.properties(affected_files=['testing/buildbot/fake-group.json']),
        api.chromium_tests_builder_config.try_build(
            builder_group='fake-try-group',
            builder='fake-try-builder',
            builder_db=ctbc.BuilderDatabase.create({
                'fake-group': {
                    'fake-builder':
                        ctbc.BuilderSpec.create(
                            chromium_config='chromium',
                            gclient_config='chromium',
                        ),
                },
            }),
            try_db=ctbc.TryDatabase.create({
                'fake-try-group': {
                    'fake-try-builder':
                        ctbc.TrySpec.create_for_single_mirror(
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
