# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'goma',
]


def RunSteps(api):
  api.goma.ensure_goma(client_type='candidate')
  api.goma.set_client_flags('goma.chromium.org', '?prod')
  api.goma.start()


def GenTests(api):
  yield api.test('basic')
