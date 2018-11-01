# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'commit_position',
]


def RunSteps(api):
  api.commit_position.chromium_commit_position_from_hash(
      '01234567890abcdef01234567890abcdef01234567')


def GenTests(api):
  yield (
      api.test('invalid') +
      api.post_process(post_process.StatusFailure) +
      api.post_process(
          post_process.ResultReasonRE,
          r'^Could not parse commit position from git output: $') +
      api.post_process(post_process.DropExpectation)
  )
