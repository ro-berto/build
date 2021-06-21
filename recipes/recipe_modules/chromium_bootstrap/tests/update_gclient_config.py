# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from PB.go.chromium.org.luci.buildbucket.proto import common

DEPS = [
    'chromium_bootstrap',
    'depot_tools/gclient',
    'recipe_engine/assertions',
    'recipe_engine/properties',
]

DEFAULT_REPO = 'fake-repo'
DEFAULT_HASH = 'default-hash'


def RunSteps(api):
  gclient_config = api.gclient.make_config()
  gclient_config.repo_path_map.update(api.properties.get('repo_path_map', {}))
  assert not gclient_config.revisions
  api.chromium_bootstrap.update_gclient_config(gclient_config)
  api.assertions.assertEqual(gclient_config.revisions,
                             api.properties['expected_revisions'])


def GenTests(api):

  def repo_path_map(paths_by_repo):
    return api.properties(
        repo_path_map={k: (v, 'HEAD') for k, v in paths_by_repo.iteritems()})

  def expect_revisions(revisions):
    return sum([
        api.properties(expected_revisions=revisions),
        api.post_check(post_process.StatusSuccess),
        api.post_process(post_process.DropExpectation),
    ], api.empty_test_data())

  yield api.test(
      'not-bootstrapped',
      expect_revisions({}),
  )

  commits = [
      common.GitilesCommit(
          host='chromium.googlesource.com',
          project='chromium/src',
          ref='refs/heads/main',
          id='src-hash',
      ),
      common.GitilesCommit(
          host='chrome-internal.googlesource.com',
          project='chrome/src-internal',
          ref='refs/heads/main',
          id='src-internal-hash',
      ),
  ]

  yield api.test(
      'bootstrapped',
      api.chromium_bootstrap.properties(commits=commits),
      repo_path_map({
          'https://chromium.googlesource.com/chromium/src':
              'src',
          'https://chrome-internal.googlesource.com/chrome/src-internal':
              'src-internal',
      }),
      expect_revisions({
          'src': 'src-hash',
          'src-internal': 'src-internal-hash',
      }),
  )

  yield api.test(
      'bootstrapped-with-missing-repo-path-map-entry',
      api.chromium_bootstrap.properties(commits=commits),
      repo_path_map({
          'https://chromium.googlesource.com/chromium/src': 'src',
      }),
      api.post_check(post_process.StatusException),
      api.post_check(
          post_process.ResultReasonRE,
          ('repo_path_map does not contain an entry for '
           r'https://chrome-internal\.googlesource\.com/chrome/src-internal')),
      api.post_process(post_process.DropExpectation),
  )
