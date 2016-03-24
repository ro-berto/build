# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia Swarming compile.


DEPS = [
  'recipe_engine/platform',
  'recipe_engine/properties',
  'skia',
]


def RunSteps(api):
  api.skia.setup(running_in_swarming=True)
  api.skia.compile_steps()


def GenTests(api):
  b = 'Build-Win-MSVC-x86-Debug-VS2015'
  yield (
      api.test(b) +
      api.properties(buildername=b,
                     mastername='client.skia.compile',
                     slavename='skiabot-win-compile-000',
                     buildnumber='2',
                     revision='abc123',
                     swarm_out_dir='[SWARM_OUT]') +
      api.platform('win', 64)
  )
