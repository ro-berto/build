# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A recipe for picking and tagging a stable revision for chromium/src.

This recipe picks a commit of codesearch/chromium/src at HEAD, adds a ref to
it so it won't be garabage collected once a new synthetic commit is created
and then triggers the other codesearch recipes with both the chosen commit hash
and the hash to the parent commit as parameters. This ensures that codesearch
index packs (used to generate xrefs) are all generated from the same revision,
but are marked by kythe with the synthetic commit hash so cross references can
linked by commit hash.
"""

from datetime import datetime

DEPS = [
    'depot_tools/git',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/scheduler',
    'recipe_engine/step',
    'recipe_engine/time',
    'recipe_engine/url',
]

BUILDERS = [
    'codesearch-gen-chromium-android',
    'codesearch-gen-chromium-chromiumos',
    'codesearch-gen-chromium-fuchsia',
    'codesearch-gen-chromium-lacros',
    'codesearch-gen-chromium-linux',
    'codesearch-gen-chromium-win',
]

SOURCE_REPO = 'https://chromium.googlesource.com/codesearch/chromium/src'


def RunSteps(api):
  env = {
      # Turn off the low speed limit, since checkout will be long.
      'GIT_HTTP_LOW_SPEED_LIMIT': '0',
      'GIT_HTTP_LOW_SPEED_TIME': '0',
  }

  checkout_dir = api.path['cache'].join('builder')
  if not api.file.glob_paths('Check for existing checkout', checkout_dir,
                             'src'):
    with api.context(cwd=checkout_dir, env=env):
      api.git('clone', '--progress', SOURCE_REPO, 'src')

  api.path['checkout'] = checkout_dir.join('src')
  with api.context(cwd=api.path['checkout'], env=env):
    # Discard any commits from previous runs.
    api.git('reset', '--hard', 'HEAD')

    api.git('fetch')

    mirror_hash = api.git(
        'rev-parse',
        'FETCH_HEAD',
        name='fetch mirror hash',
        stdout=api.raw_io.output_text()).stdout.strip()

    mirror_unix_timestamp = int(
        api.git(
            'log',
            '-1',
            '--format=%ct',
            'FETCH_HEAD',
            name='fetch mirror timestamp',
            stdout=api.raw_io.output_text()).stdout.strip())

    commit_hash = api.git(
        'rev-parse',
        'FETCH_HEAD^',
        name='fetch source hash',
        stdout=api.raw_io.output_text()).stdout.strip()

    unix_timestamp = int(
        api.git(
            'log',
            '-1',
            '--format=%ct',
            'FETCH_HEAD^',
            name='fetch source timestamp',
            stdout=api.raw_io.output_text()).stdout.strip())

    # The head of SOURCE_REPO will be lost the next time a synthetic commit
    # is added to codesource/chromium/src.  Add a ref to the current head so
    # that it doesn't get garbage collected, and references to it in codesearch
    # links stay valid.
    api.git('push', SOURCE_REPO, mirror_hash + ':refs/kythe/' + commit_hash)

    # Trigger the chromium_codesearch builders.
    properties = {
        'root_solution_revision': commit_hash,
        'root_solution_revision_timestamp': unix_timestamp,
        'codesearch_mirror_revision': mirror_hash,
        'codesearch_mirror_revision_timestamp': mirror_unix_timestamp
    }

    api.scheduler.emit_trigger(
        api.scheduler.BuildbucketTrigger(properties=properties),
        project='infra',
        jobs=BUILDERS)


def GenTests(api):
  yield (api.test('basic', api.runtime(is_luci=True, is_experimental=False)) +
         api.step_data('fetch mirror hash',
                       api.raw_io.stream_output('a' * 40, stream='stdout')) +
         api.step_data('fetch mirror timestamp',
                       api.raw_io.stream_output('100', stream='stdout')) +
         api.step_data('fetch source hash',
                       api.raw_io.stream_output('b' * 40, stream='stdout')) +
         api.step_data('fetch source timestamp',
                       api.raw_io.stream_output('50', stream='stdout')))
