# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe for running ChromeProxy integration tests on desktop VM's."""

DEPS = [
    'bot_update',
    'chromium',
    'gclient',
    'path',
    'properties',
    'step',
]


def RunSteps(api):
  # Get the latest checkout, retrieves test code.
  api.step('Pulling down Chromium', ['echo', 'Pulling down Chromium'])
  api.chromium.set_config('chromium')
  api.gclient.set_config('chromium')
  api.bot_update.ensure_checkout(force=True)

  # Build Chrome with Ninja
  api.step('Build Chrome', ['echo', 'Building Chrome'])
  api.chromium.c.gyp_env.GYP_GENERATORS.add('ninja')
  api.chromium.runhooks()
  api.chromium.compile(targets=['chrome'])

  # Try running a sample test
  api.step('Run Sample Smoke Test',
      [api.path['checkout'].join('tools', 'chrome_proxy', 'run_benchmark'),
       '--use-live-sites', '--browser=release',
       '--chrome-root=%s' % api.path['checkout'],
       '--extra-browser-args="--no-sandbox"',
       'chrome_proxy_benchmark.smoke.smoke'])

def GenTests(api):
  yield (
      api.properties.generic()
  )
