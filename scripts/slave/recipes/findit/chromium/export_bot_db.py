# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Export the bot db to cloud storage."""

import attr
import collections
import json

from recipe_engine import post_process, types

from RECIPE_MODULES.build.chromium_tests import (bot_db as bot_db_module,
                                                 bot_spec, steps)

DEPS = [
    'chromium_tests',
    'depot_tools/gsutil',
    'recipe_engine/raw_io',
    'recipe_engine/properties',
]


def _bot_db_to_json(bot_db):

  def encode(obj):
    if isinstance(obj, types.FrozenDict):
      return dict(obj)
    if attr.has(type(obj)):
      return attr.asdict(obj, dict_factory=collections.OrderedDict)
    return None

  return json.dumps(bot_db.builders_by_group, default=encode)


def RunSteps(api):
  bucket = api.properties['gs_bucket']
  object_path = api.properties['gs_object']
  builders_json = _bot_db_to_json(api.chromium_tests.builders)
  api.gsutil.upload(api.raw_io.input(builders_json), bucket, object_path)


def GenTests(api):
  yield api.test(
      'with_mock_bdb',
      api.properties(gs_bucket='bucket', gs_object='data.json'),
      api.chromium_tests.builders(
          bot_db_module.BotDatabase.create({
              'mockgroup': {
                  'mockbuilder':
                      bot_spec.BotSpec.create(
                          compile_targets=['foo', 'bar'],
                          test_specs=[
                              bot_spec.TestSpec.create(steps.SizesStep,
                                                       'fake-url',
                                                       'fake-config-name')
                          ],
                      ),
              }
          })),
  )
  yield api.test(
      'with_real_bdb_no_expect',
      api.properties(gs_bucket='bucket', gs_object='data.json'),
      api.post_process(post_process.DropExpectation),
  )
