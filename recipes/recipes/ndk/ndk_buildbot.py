# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
    'chromite',
    'ndk',
    'recipe_engine/properties',
]

# Map group name to 'chromite' configuration name.
_GROUP_CONFIG_MAP = {
    'client.ndk': {
        'group_config': 'chromite_config',
    },
}


def RunSteps(api):
  api.chromite.configure(api.properties, _GROUP_CONFIG_MAP)
  api.chromite.run_cbuildbot(args=['--buildbot'])


def GenTests(api):
  yield api.test(
      'basic',
      api.builder_group.for_current('client.ndk'),
      api.properties.generic(
          branch='master',
          cbb_config='ndk-linux-arm64-v8a',
      ),
  )
