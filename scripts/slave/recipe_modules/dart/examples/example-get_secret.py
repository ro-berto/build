# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (Filter)

DEPS = [
  'dart',
  'recipe_engine/platform',
]

def RunSteps(api):
  api.dart.get_secret('not_a_secret')

def GenTests(api):
  yield api.test('basic')
  yield api.test(
      'win',
      api.platform('win', 64),
      api.post_process(Filter('cloudkms get key')),
  )
