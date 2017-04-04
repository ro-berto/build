# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromite',
  'gitiles',
  'recipe_engine/properties',
]


_TEST_CONFIG = {
  '_default': {
    'foo': 'bar',
    'baz': 'qux',
  },
  '_templates': {
    'woot': {
      'baz': 'templated',
    }
  },
  'myconfig': {
    '_template': 'woot',
    'local': 'variable',
  },
}

def RunSteps(api):
  api.chromite.set_config('base')

  # Basic checkout exercise.
  api.chromite.cbuildbot('cbuildbot', 'amd64-generic-full',
                         args=['--clobber', '--build-dir', '/here/there'])


def GenTests(api):
  yield (
      api.test('basic') +
      # chromite module uses path['root'] which exists only in Buildbot.
      api.properties(path_config='buildbot')
  )

  yield (
      api.test('pass_repo_sync_args') +
      # chromite module uses path['root'] which exists only in Buildbot.
      api.properties(path_config='buildbot',
                     repo_sync_args=['-j16'])
  )
