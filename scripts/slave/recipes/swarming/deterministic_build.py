# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test the deterministic build.

Waterfall page: https://build.chromium.org/p/chromium.swarm/waterfall
"""

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'json',
  'platform',
  'properties',
  'step',
]


def GenSteps(api):
  api.chromium.set_config('chromium_no_goma',
                          api.properties.get('configuration', 'Release'))
  api.gclient.set_config('chromium')

  # Checkout chromium.
  api.bot_update.ensure_checkout(force=True)
  api.chromium.runhooks()

  api.chromium.compile(targets=['base_unittests'], force_clobber=True)


def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    for configuration in ('Debug', 'Release'):
      yield (
        api.test('%s_%s' % (platform, configuration)) +
        api.platform.name(platform) +
        api.properties.scheduled() +
        api.properties(configuration=configuration)
      )
