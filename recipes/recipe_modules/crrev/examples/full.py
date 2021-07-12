# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api

DEPS = [
    'crrev',
    'recipe_engine/properties',
    'recipe_engine/step',
    'recipe_engine/json',
]


def RunSteps(api):
  cp = api.properties['commit_position']
  try:
    api.crrev.to_commit_hash(cp)
  except ValueError:
    raise recipe_api.StepFailure('Invalid commit position: %s' % cp)


def GenTests(api):
  yield api.test(
      'invalid_commit_position',
      api.properties(commit_position='foo'),
  )

  yield api.test(
      'valid_commit_position',
      api.properties(commit_position='refs/heads/master@{#111}'),
      api.step_data(
          name='crrev get commit hash for refs/heads/master@{#111}',
          stdout=api.json.output({
              'git_sha': 'abcdeabcde0123456789abcdeabcde0123456789'
          })),
  )

  yield api.test(
      'empty_commit_hash_output',
      api.properties(commit_position='refs/heads/master@{#111}'),
      api.step_data(
          name='crrev get commit hash for refs/heads/master@{#111}',
          stdout=api.json.output({})),
  )
