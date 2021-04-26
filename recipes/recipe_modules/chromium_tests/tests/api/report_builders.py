# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
]

BUILDERS = ctbc.BuilderDatabase.create({
    'fake-group': {
        'fake-builder': ctbc.BuilderSpec.create(),
    },
})

TRYBOTS = ctbc.TryDatabase.create({
    'fake-try-group': {
        'fake-try-builder':
            ctbc.TrySpec.create_for_single_mirror(
                builder_group='fake-group',
                buildername='fake-builder',
            ),
    },
})


def RunSteps(api):
  _, builder_config = api.chromium_tests_builder_config.lookup_builder(
      builder_db=BUILDERS, try_db=TRYBOTS)
  api.chromium_tests.report_builders(builder_config)


def check_link(check, steps, expected_link):
  check(steps['report builders'].links['fake-builder'] == expected_link)


def GenTests(api):
  for bucket, link_bucket in (
      ('try', 'ci'),
      ('try-beta', 'ci-beta'),
      ('try-stable', 'ci-stable'),
  ):
    expected_link = (
        'https://ci.chromium.org/p/chromium/builders/%s/fake-builder' %
        link_bucket)
    yield api.test(
        bucket,
        api.chromium.try_build(
            bucket=bucket,
            builder_group='fake-try-group',
            builder='fake-try-builder',
        ),
        api.post_check(check_link, expected_link),
        api.post_process(post_process.DropExpectation),
    )
