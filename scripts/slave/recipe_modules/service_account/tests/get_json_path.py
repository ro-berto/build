# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/step',
    'service_account',
]


def RunSteps(api):
  api.step('json path', [])
  p = api.step.active_result.presentation
  p.step_text = api.service_account.get_json_path('foo')


def GenTests(api):
  yield api.test('basic')
