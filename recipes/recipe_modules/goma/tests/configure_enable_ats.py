# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'goma',
]


def RunSteps(api):
  api.goma.ensure_goma(client_type='candidate')
  api.goma.configure_enable_ats()
  api.goma.start()


def GenTests(api):
  yield api.test(
      'basic',
      api.goma(server_host='goma.chromium.org', rpc_extra_params="?prod"),
  )
