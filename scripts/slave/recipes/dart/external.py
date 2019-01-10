# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

DEPS = [
  'recipe_engine/properties',
  'recipe_engine/step',
]

def RunSteps(api):
  result = api.properties.get('result')
  assert(result)
  url = api.properties.get('url')
  assert(url)
  api.step('process properties', None)
  api.step.active_result.presentation.links['results'] = url
  if 'success' not in result:
    raise api.step.StepFailure(result)

def GenTests(api):
  yield (
    api.test('success') +
    api.properties.generic(
      result='success',
      url='https://www.example.com')
  )
  yield (
    api.test('failure') +
    api.properties.generic(
      result='failure',
      url='https://www.example.com')
  )
