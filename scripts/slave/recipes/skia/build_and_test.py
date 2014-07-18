# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


DEPS = [
  'path',
  'properties',
  'skia',
]


def GenSteps(api):
  api.skia.setup()
  yield api.skia.common_steps()
  role = api.skia.c.BUILDER_NAME.split('-')[0]

  if role == 'Test':
    yield api.skia.test_steps()

  # Run the Perf steps on Test bots in Debug mode to catch any assertions.
  if (role == 'Perf' or
      (role == 'Test' and 'Debug' in api.skia.c.BUILDER_NAME)):
    yield api.skia.perf_steps()

def GenTests(api):
  builders = [
    'Perf-ChromeOS-Daisy-MaliT604-Arm7-Release',
    'Test-Android-Nexus10-MaliT604-Arm7-Release',
    'Test-Android-Xoom-Tegra2-Arm7-Release',
    'Test-Mac10.8-MacMini4.1-GeForce320M-x86_64-Debug',
    'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Release-Valgrind',
    'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Debug-ZeroGPUCache',
    'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug',
    'Test-Ubuntu13.10-GCE-NoGPU-x86_64-Release-TSAN',
    'Test-Win7-ShuttleA-HD2000-x86-Release',
    'Test-Win7-ShuttleA-HD2000-x86-Release-ANGLE',
  ]
  for builder in builders:
    yield (
      api.test(builder) +
      api.properties(buildername=builder) +
      api.path.exists(
          api.path['slave_build'].join('gm', 'expected',
                                       'expected-results.json'),
          api.path['slave_build'].join('gm', 'expected',
                                       'ignored-tests.txt'),
      )
    )
