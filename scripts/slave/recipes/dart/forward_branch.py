# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
  'dart',
  'depot_tools/git',
  'recipe_engine/buildbucket',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'recipe_engine/raw_io',
]


def RunSteps(api):
  clobber = 'clobber' in api.properties
  api.dart.checkout(clobber)
  dart = api.dart.dart_executable()
  find_base_commit = api.path['checkout'].join(
      'tools', 'bots', 'find_base_commit.dart')
  result = api.step('find base commit', [dart, find_base_commit],
      stdout=api.raw_io.output_text(add_output_log=True))
  commit_hash = result.stdout.strip()
  # todo(athom): use something like api.buildbucket.gitiles_commit.ref instead
  # The base branch is fast forwarded to the most recent commit with a complete
  # set of test results. find_base_commit.dart is responsible for identifying
  # that commit.
  ref = 'refs/heads/base'
  # Guard against the empty string here to avoid deleting the remote branch
  assert(commit_hash)
  api.git('push', 'https://dart.googlesource.com/sdk.git',
      '%s:%s' % (commit_hash, ref),
      name='push %s to %s' % (commit_hash, ref))


def GenTests(api):
  yield (api.test('base') +
      api.step_data('find base commit',
                    stdout=api.raw_io.output('deadbeef')) +
      api.buildbucket.ci_build(
          project='dart',
          bucket='ci',
          builder='base',
          git_repo='https://dart.googlesource.com/a/sdk.git'))

  yield (api.test('no_hash') +
      api.step_data('find base commit',
                    stdout=api.raw_io.output('  ')) +
      api.buildbucket.ci_build(
          project='dart',
          bucket='ci',
          builder='base',
          git_repo='https://dart.googlesource.com/a/sdk.git') +
      api.expect_exception('AssertionError') +
      api.post_process(post_process.DropExpectation) +
      api.post_process(post_process.DoesNotRunRE, 'push.*'))
