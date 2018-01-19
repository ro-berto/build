# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromite',
    'ndk',
    'recipe_engine/properties',
]


# Map master name to 'chromite' configuration name.
_MASTER_CONFIG_MAP = {
  'client.ndk': {
    'master_config': 'chromite_config',
  },
}


def RunSteps(api):
  api.chromite.configure(api.properties, _MASTER_CONFIG_MAP)
  api.chromite.run_cbuildbot(args=['--buildbot'])


def GenTests(api):
  yield (
    api.test('basic') +
    api.properties.generic(
      mastername='client.ndk',
      branch='master',
      cbb_config='ndk-linux-arm64-v8a',
      # chromite module uses path['root'] which exists only in Buildbot.
      path_config='buildbot',
    )
  )
