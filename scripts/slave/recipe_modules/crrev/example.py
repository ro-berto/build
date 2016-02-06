# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

DEPS = [
    'crrev',
    'recipe_engine/properties',
    'recipe_engine/step',
    'recipe_engine/raw_io',
]

def RunSteps(api):
  # Try to resolve a commit position to a hash
  if 'commit_position' in api.properties.keys():
    api.crrev.chromium_hash_from_commit_position(
        api.properties['commit_position'])

  # Try to resolve a hash to a commit_position
  if 'commit_hash' in api.properties.keys():
    api.crrev.chromium_commit_position_from_hash(
        api.properties['commit_hash'])


def GenTests(api):
  yield (
      api.test('invalid_commit_position') +
      api.properties(commit_position='foo'))

  yield (
      api.test('invalid_hash') +
      api.properties(commit_hash='foo'))

  yield (
      api.test('valid_hash') +
      api.properties(commit_hash='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa') +
      api.step_data(
          name='resolving hash aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
          stdout=api.raw_io.output('11111')))

  yield (
      api.test('valid_comit_position') +
      api.properties(commit_position='11111') +
      api.step_data(
          name='resolving commit_pos 11111',
          stdout=api.raw_io.output('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')))

  yield (
      api.test('invalid_commit_hash_output') +
      api.properties(commit_position='11111') +
      api.step_data(
          name='resolving commit_pos 11111',
          stdout=api.raw_io.output('not a sha1 hash')))

  yield (
      api.test('invalid_commit_position_output') +
      api.properties(commit_hash='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa') +
      api.step_data(
          name='resolving hash aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
          stdout=api.raw_io.output('not an integer')))
