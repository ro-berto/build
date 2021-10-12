# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
  'chromium',
  'recipe_engine/assertions'
]


def RunSteps(api):
  version = api.chromium.get_version()
  api.assertions.assertEqual(version, {
      'MAJOR': '51',
      'MINOR': '0',
      'BUILD': '2704',
      'PATCH': '0',
  })


def GenTests(api):
  yield api.test(
      'basic',
      api.post_process(post_process.DropExpectation),
  )
