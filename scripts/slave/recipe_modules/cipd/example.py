# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'file',
  'path',
  'platform',
  'step',
  'cipd',
]

def RunSteps(api):
  # Prepare files.
  temp = api.path.mkdtemp('cipd-example')

  api.cipd.install_client("install cipd")

  pkgs = {
    "infra/monitoring/dispatcher/linux-amd64": {
      'version': '7f751b2237df2fdf3c1405be00590fefffbaea2d',
    },
  }

  api.cipd.ensure_installed(temp.join('bin'), pkgs)

  api.cipd.platform_tag()

  # Clean up.
  api.file.rmtree('cleanup', temp)


def GenTests(api):
  yield api.test('basic')
  yield api.test('mac64') + api.platform('mac', 64)
  yield api.test('install-failed') + api.step_data('install cipd', retcode=1)

