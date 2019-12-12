# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
]

BUILDERS = {
    'fake-master': {
        'builders': {
            'fake-builder': {}
        },
    },
}

TRYBOTS = {
    'fake-try-master': {
        'builders': {
            'fake-try-builder': {
                'bot_ids': [{
                    'mastername': 'fake-master',
                    'buildername': 'fake-builder',
                }],
            },
        },
    },
}


def RunSteps(api):
  bot = api.chromium_tests._lookup_bot_metadata(
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
            mastername='fake-try-master',
            builder='fake-try-builder',
        ),
        api.post_check(check_link, expected_link),
        api.post_process(post_process.DropExpectation),
    )
