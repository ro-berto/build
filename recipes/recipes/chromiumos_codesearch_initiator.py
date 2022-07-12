# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Initialize ChromiumOS codesearch builders to create kzips.

Checks out chromiumos manifest repo and uses the latest snapshot commit hash
to initialize chromiumos codesearch builders.
"""

from recipe_engine.post_process import LogContains

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

BUILDERS = [
    'codesearch-gen-chromiumos-amd64-generic',
    'codesearch-gen-chromiumos-arm-generic',
    'codesearch-gen-chromiumos-arm64-generic',
]

CODESEARCH_REPO = 'https://chromium.googlesource.com/chromiumos/codesearch'
MANIFEST_REPO = 'https://chromium.googlesource.com/chromiumos/manifest'


def latestRefInfo(api, clone_dir, repo, branch=None):
  """Return the hash and timestamp of the latest commit on a branch."""
  clone_base_dir = api.context.cwd or api.path['cache'].join('builder')
  if not api.file.glob_paths('Check for existing checkout', clone_base_dir,
                             clone_dir):
    with api.context(cwd=clone_base_dir):
      clone_args = ['--depth=1']
      if branch:
        clone_args.extend(['-b', branch])
      clone_args.extend([
          repo,
          clone_dir,
      ])

      api.git(
          'clone',
          *clone_args,
          name='clone %s of %s' % (branch or 'HEAD', repo))

  with api.context(cwd=clone_base_dir.join(clone_dir)):
    api.git('fetch')

    commit_hash = api.git(
        'rev-parse', 'HEAD', name='fetch hash',
        stdout=api.raw_io.output_text()).stdout.strip()
    timestamp = api.git(
        'log',
        '-1',
        '--format=%ct',
        'HEAD',
        name='fetch timestamp',
        stdout=api.raw_io.output_text()).stdout.strip()

    return commit_hash, timestamp


def RunSteps(api):
  mirror_hash, mirror_unix_timestamp = latestRefInfo(api,
                                                     'chromiumos_codesearch',
                                                     CODESEARCH_REPO)
  manifest_hash, _ = latestRefInfo(api, 'chromiumos_manifest', MANIFEST_REPO,
                                   'stable')

  # Trigger the chromiumos_codesearch builders.
  properties = {
      'codesearch_mirror_revision': mirror_hash,
      'codesearch_mirror_revision_timestamp': mirror_unix_timestamp,
      'manifest_hash': manifest_hash,
  }

  api.scheduler.emit_trigger(
      api.scheduler.BuildbucketTrigger(properties=properties),
      project='infra',
      jobs=BUILDERS)


# TODO(crbug/1284439): Add more tests.
def GenTests(api):
  yield api.test(
      'basic',
      api.step_data('fetch hash',
                    api.raw_io.stream_output_text('d3adb33f', stream='stdout')),
      api.post_process(LogContains, 'luci-scheduler.EmitTriggers', 'input',
                       ['d3adb33f']))
