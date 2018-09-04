# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'findit',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.path['checkout'] = api.path.mkdtemp('fake_checkout')
  revision = api.properties['revision']
  solution_name = api.properties.get('solution_name')
  api.findit.files_changed_by_revision(revision, solution_name)


def GenTests(api):
  yield api.test('affected_files_in_src') + api.properties(
      revision='a' * 40,
      solution_name='src',
  )
  yield api.test('affected_files_third_party') + api.properties(
      revision='a' * 40,
      solution_name='src/third_party/pdfium',
  )
  yield (
      api.test('affected_files_on_win') +
      api.platform.name('win') +
      api.properties(
          revision='a' * 40,
          solution_name='src\\third_party\\pdfium',
      )
  )
