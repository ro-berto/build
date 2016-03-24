# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia Swarming test.


DEPS = [
  'recipe_engine/properties',
  'skia',
]


def RunSteps(api):
  api.skia.setup(running_in_swarming=True)
  api.skia.test_steps()
  api.skia.cleanup_steps()


def GenTests(api):
  b = 'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug'
  yield (
      api.test(b) +
      api.properties(buildername=b,
                     mastername='client.skia',
                     slavename='skiabot-linux-tester-000',
                     buildnumber='2',
                     revision='abc123',
                     swarm_out_dir='[SWARM_OUT]')
  )
