# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/step',
  'wct',
]


def RunSteps(api):
  temp = api.path.mkdtemp('wct-test')
  api.step('package.json', ['touch', temp.join('package.json')])
  api.path.mock_add_paths(temp.join('package.json'))
  api.wct.install()
  api.wct.run(temp)
  api.file.rmtree('cleanup', temp)


def GenTests(api):
  yield api.test('linux') + api.platform.name('linux')
  yield api.test('notlinux') + api.platform.name('win')
