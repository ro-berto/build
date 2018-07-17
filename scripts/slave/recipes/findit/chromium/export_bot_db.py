# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Export the bot db to cloud storage."""

import collections
import json

from recipe_engine.post_process import DropExpectation


DEPS = [
    'chromium_tests',
    'depot_tools/gsutil',
    'recipe_engine/json',
    'recipe_engine/properties',
]


def thaw_and_remove_unserializable(v):
  if isinstance(v, collections.Mapping):
    return {
        thaw_and_remove_unserializable(k): thaw_and_remove_unserializable(v)
        for k, v in v.items()}
  if isinstance(v, (list, tuple, set, frozenset)):
    return [thaw_and_remove_unserializable(e) for e in v]
  try:
    json.dumps(v)
  except TypeError:
    return None
  return v


def RunSteps(api):
  bucket = api.properties['gs_bucket']
  object_path = api.properties['gs_object']
  # We allow overriding the content to export from a property to allow test to
  # inject values, as we don't want to have the expectations of this recipe
  # change every time the bot_db changes, also because it's massive.
  builders = thaw_and_remove_unserializable(
      api.properties.get('builders') or api.chromium_tests.builders)
  api.gsutil.upload(api.json.input(builders), bucket, object_path)


def GenTests(api):
  yield api.test('with_mock_bdb') + api.properties(
      gs_bucket='bucket',
      gs_object='data.json',
      builders={
          'mockmaster': {
              'mockbuilder': {
                  # Something frozen.
                  'something': frozenset([]),
                  # Something not serializable.
                  'something_else': object()}}})
  yield api.test('with_real_bdb_no_expect') + api.properties(
      gs_bucket='bucket',
      gs_object='data.json') + api.post_process(DropExpectation)
