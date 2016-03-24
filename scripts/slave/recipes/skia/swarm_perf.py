# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia Swarming perf.


DEPS = [
  'recipe_engine/platform',
  'recipe_engine/properties',
  'skia',
]


def RunSteps(api):
  api.skia.setup(running_in_swarming=True)
  api.skia.perf_steps()
  api.skia.cleanup_steps()


def GenTests(api):
  b = 'Perf-Win8-MSVC-ShuttleB-GPU-HD4600-x86_64-Release-Trybot'
  yield (
      api.test(b) +
      api.properties(buildername=b,
                     mastername='client.skia',
                     slavename='skiabot-shuttle-win8-i7-4790k-001',
                     buildnumber='2',
                     revision='abc123',
                     issue='123456',
                     patchset='20001',
                     rietveld='https://codereview.chromium.org',
                     swarm_out_dir='[SWARM_OUT]') +
      api.platform('win', 64)
  )
