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
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'v8',
  'zip',
]

ARCHIVE_LINK = 'https://storage.googleapis.com/chromium-v8/official/%s/%s'
BRANCH_RE = re.compile(r'^\d+\.\d+(?:\.\d+)?$')
RELEASE_BRANCH_RE = re.compile(r'^\d+\.\d+$')
FIRST_BUILD_IN_MILESTONE_RE = re.compile(r'^\d+\.\d+\.\d+$')


def make_archive(api, branch, version, archive_type, step_suffix='',
                 archive_suffix=''):
  # Make a list of files to archive.
  build_dir = api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)
  file_list_test_data = map(str, map(build_dir.join, ['d8', 'icudtl.dat']))
  file_list = api.python(
      'filter build files' + step_suffix,
      api.path['checkout'].join('tools', 'release', 'filter_build_files.py'),
      [
        '--dir', build_dir,
        '--platform', api.chromium.c.TARGET_PLATFORM,
        '--type', archive_type,
        '--json-output', api.json.output(),
      ],
      infra_step=True,
      step_test_data=lambda: api.json.test_api.output(file_list_test_data),
  ).json.output

  # Zip build.
  zip_file = api.path['cleanup'].join('archive.zip')
  package = api.zip.make_package(build_dir, zip_file)
  map(package.add_file, map(api.path.abs_to_path, file_list))
  package.zip('zipping' + step_suffix)

  # Upload to google storage bucket.
  if api.chromium.c.TARGET_ARCH != 'intel':
    # Only disambiguate non-intel architectures. This is closest to our naming
    # conventions.
    arch_name = '-%s' % api.chromium.c.TARGET_ARCH
  else:
    arch_name = ''
  archive_name = (
      'v8-%s%s%s%s-rel-%s.zip' %
      (api.chromium.c.TARGET_PLATFORM, arch_name, api.chromium.c.TARGET_BITS,
       archive_suffix, version)
  )
  gs_path_suffix = branch if RELEASE_BRANCH_RE.match(branch) else 'canary'
  api.gsutil.upload(
      zip_file,
      'chromium-v8/official/%s' % gs_path_suffix,
      archive_name,
      args=['-a', 'public-read'],
      name='upload' + step_suffix,
  )

  # Upload first build for the latest milestone to a known location. We use
  # these binaries for running reference perf tests.
  if (RELEASE_BRANCH_RE.match(branch) and
      FIRST_BUILD_IN_MILESTONE_RE.match(version)):
    api.gsutil.upload(
        zip_file,
        'chromium-v8/official/refbuild',
        'v8-%s%s%s%s-rel.zip' % (api.chromium.c.TARGET_PLATFORM, arch_name,
                                 api.chromium.c.TARGET_BITS, archive_suffix),
        args=['-a', 'public-read'],
        name='update refbuild binaries' + step_suffix,
    )



  api.step('archive link' + step_suffix, cmd=None)
  api.step.active_result.presentation.links['download'] = (
      ARCHIVE_LINK % (gs_path_suffix, archive_name))


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

  make_archive(api, branch, version, 'exe')
  make_archive(api, branch, version, 'lib', ' (libs)', '-libs')


def GenTests(api):
  for mastername, _, buildername, bot_config in api.v8.iter_builders(
      'v8/archive'):
    test = (
        api.test(api.v8.test_name(mastername, buildername)) +
        api.properties.generic(mastername=mastername,
                               buildername=buildername,
                               branch='3.4',
                               revision='deadbeef') +
        api.platform(bot_config['testing']['platform'], 64) +
        api.v8.version_file(17, 'head') +
        api.override_step_data(
            'git describe', api.raw_io.stream_output('3.4.3.17')) +
        api.v8.check_param_equals(
            'bot_update', '--revision', 'v8@refs/branch-heads/3.4:deadbeef') +
        api.v8.check_param_equals(
            'bot_update', '--with_branch_heads', True) +
        api.post_process(
            MustRun, 'clobber', 'gclient runhooks', 'gn', 'compile',
            'zipping', 'gsutil upload', 'archive link')
    )

    if 'android' in buildername.lower():
      # Make sure bot_update specifies target_os on Android builders.
      test += api.v8.check_in_param(
          'bot_update', '--spec-path', 'target_os = [\'android\']')

    if buildername == 'V8 Arm32':
      # Make sure bot_update specifies target_cpu on Arm builders.
      test += api.v8.check_in_param(
          'bot_update', '--spec-path', 'target_cpu = [\'arm\']')

    test += api.post_process(Filter(
        'gn', 'compile', 'filter build files', 'zipping', 'gsutil upload',
        'archive link', 'filter build files (libs)', 'zipping (libs)',
        'gsutil upload (libs)', 'archive link (libs)'))

    yield test

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

  # Upload beta binaries to a known location.
  mastername = 'client.v8.official'
  buildername = 'V8 Linux64'
  yield (
      api.test(api.v8.test_name(mastername, buildername, 'update_beta')) +
      api.properties.generic(mastername=mastername, buildername=buildername,
                             branch='3.4', revision='deadbeef') +
      api.v8.version_file(0, 'head') +
      api.override_step_data(
        'git describe', api.raw_io.stream_output('3.4.3')) +
      api.post_process(Filter(
        'gsutil update refbuild binaries',
        'gsutil update refbuild binaries (libs)',
      ))
  )
