# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_android',
]

def RunSteps(api):
  api.chromium_android.configure_from_properties('base_config')
  api.chromium_android.provision_devices()

def GenTests(api):
  yield (api.test('warning_exit_code') +
         api.step_data('provision_devices', retcode=88))
  yield (api.test('infra_failure_exit_code') +
         api.step_data('provision_devices', retcode=87))
