# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Export the bot db to cloud storage."""

import attr
import collections
import json

from recipe_engine import engine_types, post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium_tests_builder_config',
    'depot_tools/gsutil',
    'recipe_engine/raw_io',
    'recipe_engine/properties',
]


def _bot_db_to_json(bot_db):

  def encode(obj):
    if isinstance(obj, engine_types.FrozenDict):
      return dict(obj)
    if attr.has(type(obj)):
      return attr.asdict(obj, dict_factory=collections.OrderedDict)
    return None  # pragma: no cover

  return json.dumps(bot_db.builders_by_group, default=encode)


def RunSteps(api):
  bucket = api.properties['gs_bucket']
  object_path = api.properties['gs_object']
  builders_json = _bot_db_to_json(api.chromium_tests_builder_config.builder_db)
  api.gsutil.upload(api.raw_io.input(builders_json), bucket, object_path)


def GenTests(api):
  yield api.test(
      'with_mock_bdb',
      api.properties(gs_bucket='bucket', gs_object='data.json'),
      api.chromium_tests_builder_config.builder_db(
          ctbc.BuilderDatabase.create({
              'mockgroup': {
                  'mockbuilder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          chromium_apply_config=['foo', 'bar'],
                      ),
              }
          })),
  )
  yield api.test(
      'with_real_bdb_no_expect',
      api.properties(gs_bucket='bucket', gs_object='data.json'),
      api.post_process(post_process.DropExpectation),
  )
