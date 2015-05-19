# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'auto_bisect',
  'chromium_tests',
  'platform',
  'properties',
]

def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  api.chromium_tests.configure_build(mastername, buildername)
  api.chromium_tests.prepare_checkout(mastername, buildername)
  api.auto_bisect.run_bisect_script()

def GenTests(api):
  yield (api.test('basic')
  +api.properties.tryserver(
      mastername='tryserver.chromium.perf',
      buildername='linux_perf_bisect'))
