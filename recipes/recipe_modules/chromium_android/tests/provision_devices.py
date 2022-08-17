# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('non_device_wipe_provisioning')
  api.chromium_android.provision_devices(emulators=True)


def GenTests(api):
  yield api.test('basic')
