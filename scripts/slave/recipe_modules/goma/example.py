# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'goma'
]

def GenSteps(api):
  api.goma.diagnose_goma()


def GenTests(api):
  yield api.test('basic')
