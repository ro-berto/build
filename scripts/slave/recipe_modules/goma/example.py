# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'goma',
  'step'
]

def GenSteps(api):
  api.goma.diagnose_goma()
  # check a step runs after diagnose_goma failed.
  api.step('hello', ['echo', 'kotori'])


def GenTests(api):
  yield api.test('basic')
  yield (
    api.test('basic_with_failure') +
    api.step_data('diagnose_goma', retcode=1)
  )
