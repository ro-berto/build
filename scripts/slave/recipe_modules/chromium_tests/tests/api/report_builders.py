# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
]

BUILDERS = {
    'fake-group': {
        'fake-builder': {}
    },
}

TRYBOTS = {
    'fake-try-group': {
        'fake-try-builder': {
            'mirrors': [{
                'builder_group': 'fake-group',
                'buildername': 'fake-builder',
            }],
        },
    },
}


def RunSteps(api):
  bot = api.chromium_tests.lookup_bot_metadata(
      builders=BUILDERS, mirrored_bots=TRYBOTS)
  api.chromium_tests._report_builders(bot.settings)


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
