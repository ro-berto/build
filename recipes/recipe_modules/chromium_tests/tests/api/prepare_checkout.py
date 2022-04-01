# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
]

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build import chromium_swarming
from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

from PB.recipe_modules.build.chromium_tests.properties import InputProperties

DUMMY_BUILDERS = ctbc.BuilderDatabase.create({
    'chromium.fake': {
        'cross-group-trigger-builder':
            ctbc.BuilderSpec.create(
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                },
                gclient_config='chromium',
            ),
    },
    'chromium.fake.fyi': {
        'cross-group-trigger-tester':
            ctbc.BuilderSpec.create(
                execution_mode=ctbc.TEST,
                parent_buildername='cross-group-trigger-builder',
                parent_builder_group='chromium.fake',
            ),
    },
})

PROPERTIES = {
    'runhooks_suffix': Property(default=None, kind=str),
}


def RunSteps(api, runhooks_suffix):
  _, builder_config = api.chromium_tests_builder_config.lookup_builder()
  api.chromium_tests.configure_build(builder_config)
  api.chromium_tests.prepare_checkout(
      builder_config, runhooks_suffix=runhooks_suffix)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.post_process(post_process.MustRun, 'gclient runhooks'),
  )

  yield api.test(
      'basic_try',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.post_process(post_process.MustRun, 'gclient runhooks (with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'without_patch',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(runhooks_suffix='without patch'),
      api.post_process(post_process.MustRun,
                       'gclient runhooks (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'has cache',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.step_data('builder cache.check if empty',
                    api.file.listdir(['foo', 'bar'])),
      api.post_check(lambda check, steps: check(
          'builder cache is present' in steps['builder cache'].step_text)),
      api.post_check(post_process.PropertyEquals, 'is_cached', True),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'does not have cache',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.step_data('builder cache.check if empty', api.file.listdir([])),
      api.post_check(lambda check, steps: check(
          'builder cache is absent' in steps['builder cache'].step_text)),
      api.post_check(post_process.PropertyEquals, 'is_cached', False),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cross_group_trigger',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.fake',
          builder='cross-group-trigger-builder',
          builder_db=DUMMY_BUILDERS),
      api.post_process(post_process.MustRun,
                       'read test spec (chromium.fake.fyi.json)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mirror-with-non-child-tester',
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
              'fake-tester-group': {
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.PROVIDE_TEST_SPEC),
              },
          }),
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create(mirrors=[
                          ctbc.TryMirror.create(
                              builder_group='fake-group',
                              buildername='fake-builder',
                              tester_group='fake-tester-group',
                              tester='fake-tester',
                          )
                      ]),
              },
          })),
      api.post_process(post_process.MustRun,
                       'read test spec (fake-tester-group.json)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bad-spec',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': 'invalid-spec',
      }),
      api.expect_exception('AttributeError'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bad-spec-on-related-builder',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
                  'fake-builder-with-bad-spec':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          chromium_config='chromium',
                          gclient_config='chromium',
                          parent_buildername='fake-builder',
                      ),
              },
          })),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {},
          'fake-builder-with-bad-spec': 'invalid-spec',
      }),
      api.expect_exception('AttributeError'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bad-spec-on-unrelated-builder',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
                  'fake-builder-with-bad-spec':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              },
          })),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {},
          'fake-builder-with-bad-spec': 'invalid-spec',
      }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
