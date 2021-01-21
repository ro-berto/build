# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'reclient',
]


def RunSteps(api):
  api.path['checkout'] = api.path['tmp_base'].join('checkout')
  log_dir = api.path.mkdtemp('log_dir')
  api.reclient.start_reproxy(log_dir)
  # compile chromium
  api.reclient.stop_reproxy(log_dir)
  _ = api.reclient.instance  # for code coverage
  _ = api.reclient.rewrapper_path
  _ = api.reclient.rewrapper_env
  _ = api.reclient.jobs


def GenTests(api):
  yield api.test('basic')
  yield (api.test('basic windows') + api.platform('win', 64))
  yield (api.test('override instance') +
         api.reclient.properties(instance='goma') +
         api.post_process(post_process.DropExpectation))
  yield (api.test('proper_rewrapper_flags') +
         api.reclient.properties(rewrapper_env={
             'RBE_FOO': 'foo',
             'RBE_BAR': 'bar'
         }))
  yield (api.test('incorrect_rewrapper_flags') +
         api.reclient.properties(rewrapper_env={
             'MISSING_RBE_PREFIX': 'foo',
         }) + api.expect_exception('MalformedREWrapperFlag') +
         api.post_process(post_process.DropExpectation))
