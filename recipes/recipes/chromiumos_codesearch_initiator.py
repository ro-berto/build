# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A recipe for picking and tagging a stable manifest snapshot for ChromiumOS.

This recipe initializes codesearch builders to create kzips.

TODO(crbug.com/1284439): Use snapshot to sync instead of ToT.
"""

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'depot_tools/git',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/scheduler',
    'recipe_engine/step',
    'recipe_engine/time',
    'recipe_engine/url',
]

# TODO(crbug.com/1284439): Add other builders.
BUILDERS = [
    'codesearch-gen-chromiumos-amd64-generic',
]

SOURCE_REPO = 'https://chromium.googlesource.com/chromiumos/codesearch'


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
  if not api.file.glob_paths('Check for existing checkout', checkout_dir,
                             'chromiumos_codesearch'):
    with api.context(cwd=checkout_dir):
      api.git(
          'clone',
          '--depth=1',
          SOURCE_REPO,
          'chromiumos_codesearch',
          name='clone mirror repo')

  with api.context(cwd=checkout_dir.join('chromiumos_codesearch')):
    api.git('fetch')

    mirror_hash = api.git(
        'rev-parse',
        'HEAD',
        name='fetch mirror hash',
        stdout=api.raw_io.output_text()).stdout.strip()
    mirror_unix_timestamp = api.git(
        'log',
        '-1',
        '--format=%ct',
        'HEAD',
        name='fetch mirror timestamp',
        stdout=api.raw_io.output_text()).stdout.strip()

  # Trigger the chromiumos_codesearch builders.
  properties = {
      'codesearch_mirror_revision': mirror_hash,
      'codesearch_mirror_revision_timestamp': mirror_unix_timestamp
  }

  api.scheduler.emit_trigger(
      api.scheduler.BuildbucketTrigger(properties=properties),
      project='infra',
      jobs=BUILDERS)


# TODO(crbug/1284439): Add more tests.
def GenTests(api):
  yield api.test(
      'basic',
      api.step_data('fetch mirror hash',
                    api.raw_io.stream_output_text('a' * 40, stream='stdout')),
      api.step_data('fetch mirror timestamp',
                    api.raw_io.stream_output_text('100', stream='stdout')),
  )
