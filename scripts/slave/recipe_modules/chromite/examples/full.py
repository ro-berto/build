# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromite',
  'depot_tools/gitiles',
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

  # goma.py checkout/build exercise.
  api.chromite.checkout(
      repo_sync_args=api.properties.get('repo_sync_args', None),
      branch=api.properties.get('branch', None))
  api.chromite.setup_board('amd64-generic', args=['--cache-dir', '.cache'])
  api.chromite.build_packages('amd64-generic')
  api.chromite.cros_sdk('cros_sdk', ['echo', 'hello'],
                        environ={ 'var1': 'value' })

  # Normal build exercise.
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

  yield (
      api.test('pass_branch') +
      # chromite module uses path['root'] which exists only in Buildbot.
      api.properties(path_config='buildbot',
                     branch='foobarnch') +
      api.post_process(post_process.DropExpectation)
  )
