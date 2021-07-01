# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

DEPS = [
    'isolate',
    'recipe_engine/path',
    'recipe_engine/properties',
]

PROPERTIES = {
    # TODO(crbug.com/1224266): remove this after migration.
    'use_cas':
        Property(kind=bool, help="Whether to use rbe_cas.", default=True),
}


def RunSteps(api, use_cas):
  api.isolate.isolate_tests(
      api.path['checkout'].join('out', 'Release'),
      targets=['dummy_target_1', 'dummy_target_2'],
      use_cas=use_cas)


def GenTests(api):
  yield api.test('basic')
  yield api.test('basic_isolate') + api.properties(use_cas=False)
