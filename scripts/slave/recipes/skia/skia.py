# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


DEPS = [
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'skia',
]


TEST_BUILDERS = {
  'client.skia': {
    'skiabot-linux-test-000': [
      'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug',
    ],
  },
}


def RunSteps(api):
  api.skia.gen_steps()


def GenTests(api):
  for mastername, slaves in TEST_BUILDERS.iteritems():
    for slavename, builders_by_slave in slaves.iteritems():
      for builder in builders_by_slave:
        yield (
          api.test('dummy_test') +
          api.properties(buildername=builder,
                         mastername=mastername,
                         slavename=slavename,
                         buildnumber=6,
                         revision='abc123')
        )
