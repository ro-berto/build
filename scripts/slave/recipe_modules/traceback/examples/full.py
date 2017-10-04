# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json


DEPS = [
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/step',
  'traceback',
]


def RunSteps(api):
  try:
    json.load("not a JSON")
  except Exception:
    api.step('echo', ['echo', api.traceback.format_exc()])


def GenTests(api):
  yield api.test('linux') + api.platform('linux', 64)
  yield api.test('mac') + api.platform('mac', 64)
  yield api.test('win') + api.platform('win', 32)
