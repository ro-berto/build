# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for archiving officially tagged v8 builds.
"""

import re

from recipe_engine.post_process import (
    DoesNotRun, DropExpectation, Filter, MustRun)

DEPS = [
  'chromium',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/gsutil',
  'file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'v8',
  'zip',
]

ARCHIVE_LINK = 'https://storage.googleapis.com/chromium-v8/official/%s'
BRANCH_RE = re.compile(r'^\d+\.\d+(?:\.\d+)?$')
RELEASE_BRANCH_RE = re.compile(r'^\d+\.\d+$')


def RunSteps(api):
  # Ensure a proper branch is specified.
  branch = api.properties.get('branch')
  if not branch or not BRANCH_RE.match(branch):
    api.step('Skipping due to missing release branch.', cmd=None)
    return

  api.v8.apply_bot_config(api.v8.BUILDERS)
  api.v8.checkout()

  version = str(api.v8.read_version_from_ref(api.v8.revision, 'head'))
  tags = set(x.strip() for x in api.git(
      'describe', '--tags', 'HEAD',
      stdout=api.raw_io.output_text(),
  ).stdout.strip().splitlines())

  if version not in tags:
    api.step('Skipping due to missing tag.', cmd=None)
    return

  api.v8.runhooks()
  api.v8.compile()

  # Make a list of files to archive.
  build_dir = api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)
  file_list_test_data = map(str, map(build_dir.join, ['d8', 'icudtl.dat']))
  file_list = api.python(
      'filter build files',
      api.path['checkout'].join('tools', 'release', 'filter_build_files.py'),
      [
        '--dir', build_dir,
        '--platform', api.chromium.c.TARGET_PLATFORM,
        '--output', api.json.output(),
      ],
      infra_step=True,
      step_test_data=lambda: api.json.test_api.output(file_list_test_data),
  ).json.output

  # Zip build.
  zip_file = api.path['start_dir'].join('archive.zip')
  package = api.zip.make_package(build_dir, zip_file)
  map(package.add_file, map(api.path.abs_to_path, file_list))
  package.zip('zipping')

  # Upload to google storage bucket.
  archive_name = (
      'v8-%s%s-rel-%s.zip' %
      (api.chromium.c.TARGET_PLATFORM, api.chromium.c.TARGET_BITS, version)
  )
  gs_path_suffix = branch if RELEASE_BRANCH_RE.match(branch) else 'canary'
  api.gsutil.upload(
    zip_file,
    'chromium-v8/official/%s' % gs_path_suffix,
    archive_name,
    args=['-a', 'public-read'],
  )

  api.step('archive link', cmd=None)
  api.step.active_result.presentation.links['download'] = (
      ARCHIVE_LINK % archive_name)

  # Clean up.
  api.file.remove('cleanup archive', zip_file)


def GenTests(api):
  def check_bot_update(check, steps):
    check('v8@refs/branch-heads/3.4:deadbeef' in steps['bot_update']['cmd'])

  for mastername, _, buildername, _ in api.v8.iter_builders('v8/archive'):
    yield (
        api.test(api.v8.test_name(mastername, buildername)) +
        api.properties.generic(mastername='client.v8.official',
                               buildername='V8 Linux64',
                               branch='3.4',
                               revision='deadbeef') +
        api.v8.version_file(17, 'head') +
        api.override_step_data(
            'git describe', api.raw_io.stream_output('3.4.3.17')) +
        api.post_process(check_bot_update) +
        api.post_process(
            MustRun, 'rmtree clobber', 'gclient runhooks', 'gn', 'compile',
            'zipping', 'gsutil upload', 'archive link') +
        api.post_process(Filter(
            'gn', 'compile', 'zipping', 'gsutil upload', 'archive link'))
    )

  # Test bailout on missing branch.
  mastername = 'client.v8.official'
  buildername = 'V8 Linux64'
  yield (
      api.test(api.v8.test_name(mastername, buildername, 'no_branch')) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             revision='deadbeef') +
      api.post_process(MustRun, 'Skipping due to missing release branch.') +
      api.post_process(
          DoesNotRun, 'gclient runhooks', 'gn', 'compile', 'zipping',
          'gsutil upload', 'archive link') +
      api.post_process(DropExpectation)
  )

  # Test bailout on missing tag.
  mastername = 'client.v8.official'
  buildername = 'V8 Linux64'
  yield (
      api.test(api.v8.test_name(mastername, buildername, 'no_tag')) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             branch='3.4',
                             revision='deadbeef') +
      api.v8.version_file(17, 'head') +
      api.override_step_data(
          'git describe', api.raw_io.stream_output('3.4.3.17-blabla')) +
      api.post_process(MustRun, 'Skipping due to missing tag.') +
      api.post_process(
          DoesNotRun, 'gclient runhooks', 'gn', 'compile', 'zipping',
          'gsutil upload', 'archive link') +
      api.post_process(DropExpectation)
  )
