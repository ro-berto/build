# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'commit_position',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  result = api.commit_position.chromium_hash_from_commit_position(464748)

  api.step('result', [])
  api.step.active_result.presentation.logs['details'] = [
      'result: %r' % (result,),
  ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.step_data(
          'resolving commit_pos 464748',
          stdout=api.raw_io.output_text(
              'hash:2c8b8311c920b0a7beef28c09a11a6f14abfbabc'))
  )
