# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
  'math_utils',
]


def RunSteps(api):
  api.math_utils.mean([])


def GenTests(api):
  yield api.test(
      'basic',
      api.expect_exception('ValueError'),
  )
