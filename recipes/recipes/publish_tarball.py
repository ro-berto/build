# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=line-too-long

from recipe_engine import post_process, recipe_api

import contextlib
import re

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/gsutil',
    'infra/omahaproxy',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/scheduler',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

# Sometimes a revision will be bad because the checkout will fail, causing
# publish_tarball to fail.  The version will stay in the omaha version list for
# several months and publish_tarball will keep re-running on the same broken
# version.  This blacklist exists to exclude those broken versions so the bot
# doesn't keep retrying and sending build failure emails out.
BLACKLISTED_VERSIONS = [
    '84.0.4104.56',
    '84.0.4147.4',
]


def gsutil_upload(api, source, bucket, dest, args):
  api.gsutil.upload(source, bucket, dest, args, name=str('upload ' + dest))


def published_full_tarball(version, ls_result):
  return 'chromium-%s.tar.xz' % version in ls_result


def published_lite_tarball(version, ls_result):
  return 'chromium-%s-lite.tar.xz' % version in ls_result


def published_test_tarball(version, ls_result):
  return 'chromium-%s-testdata.tar.xz' % version in ls_result


def published_nacl_tarball(version, ls_result):
  return 'chromium-%s-nacl.tar.xz' % version in ls_result


def published_all_tarballs(version, ls_result):
  return (published_full_tarball(version, ls_result) and
          published_lite_tarball(version, ls_result) and
          published_test_tarball(version, ls_result) and
          published_nacl_tarball(version, ls_result))


@recipe_api.composite_step
def export_tarball(api, args, source, destination):
  try:
    temp_dir = api.path.mkdtemp('export_tarball')
    with api.context(cwd=temp_dir):
      api.python('export_tarball', api.chromium.resource('export_tarball.py'),
                 args)
    gsutil_upload(
        api,
        api.path.join(temp_dir, source),
        'chromium-browser-official',
        destination,
        args=['-a', 'public-read'])

    hashes_result = api.python(
        'generate_hashes',
        api.chromium.resource('generate_hashes.py'),
        [api.path.join(temp_dir, source),
         api.raw_io.output()],
        step_test_data=lambda: api.raw_io.test_api.output(
            'md5  164ebd6889588da166a52ca0d57b9004  bash'))
    gsutil_upload(
        api,
        api.raw_io.input(hashes_result.raw_io.output),
        'chromium-browser-official',
        destination + '.hashes',
        args=['-a', 'public-read'])
  finally:
    api.file.rmtree('rmtree temp dir', temp_dir)


@contextlib.contextmanager
def copytree_checkout(api):
  try:
    temp_dir = api.path.mkdtemp('tmp')
    dest_dir = api.path.join(temp_dir, 'src')
    api.file.copytree('copytree', api.path['checkout'], dest_dir, symlinks=True)
    yield dest_dir
  finally:
    api.file.rmtree('rmtree temp dir', temp_dir)


@recipe_api.composite_step
def export_lite_tarball(api, version):
  # Make destructive file operations on the copy of the checkout.
  with copytree_checkout(api) as dest_dir:
    directories = [
        'android_webview',
        'buildtools/third_party/libc++',
        'chrome/android',
        'chromecast',
        'ios',
        'native_client',
        'native_client_sdk',
        'third_party/android_platform',
        'third_party/chromite',
        'third_party/closure_compiler',
        'third_party/freetype',
        'third_party/icu',
        'third_party/libjpeg_turbo',
        'third_party/libxml/src',
        'third_party/snappy',
        'third_party/webgl',
        'tools/win',
    ]
    for directory in [
        'third_party/blink/manual_tests', 'third_party/blink/perf_tests'
    ]:
      if api.path.exists(api.path.join(dest_dir, directory)):
        directories.append(directory)  # pragma: no cover

    for directory in directories:
      try:
        api.step(
            'prune %s' % directory,
            [
                'find',
                api.path.join(dest_dir, directory),
                '-type',
                'f',
                '!',
                '-iname',
                '*.gyp*',
                '!',
                '-iname',
                '*.gn*',
                '!',
                '-iname',
                '*.isolate*',
                '!',
                '-iname',
                '*.grd*',
                # This file is required for Linux afdo builds.
                # This can be removed once M87 becomes stable.
                '!',
                '-path',
                api.path.join(dest_dir, 'chrome/android/profiles/afdo.prof'),
                '-delete'
            ])
      except api.step.StepFailure:  # pragma: no cover
        # Ignore failures to delete these directories - they can be inspected
        # later to see whether they have moved to a different location
        # or deleted in different versions of the codebase.
        pass

    # Empty directories take up space in the tarball.
    api.step('prune empty directories',
             ['find', dest_dir, '-depth', '-type', 'd', '-empty', '-delete'])

    export_tarball(
        api,
        # Verbose output helps avoid a buildbot timeout when no output
        # is produced for a long time.
        [
            '--remove-nonessential-files',
            'chromium-%s' % version, '--verbose', '--progress', '--src-dir',
            dest_dir
        ],
        'chromium-%s.tar.xz' % version,
        'chromium-%s-lite.tar.xz' % version)


@recipe_api.composite_step
def export_nacl_tarball(api, version):
  # Make destructive file operations on the copy of the checkout.
  with copytree_checkout(api) as dest_dir:
    # Based on instructions from https://sites.google.com/a/chromium.org/dev/
    # nativeclient/pnacl/building-pnacl-components-for-distribution-packagers
    api.python(
        'download pnacl toolchain dependencies',
        api.path.join(dest_dir, 'native_client', 'toolchain_build',
                      'toolchain_build_pnacl.py'),
        ['--verbose', '--sync', '--sync-only', '--disable-git-cache'])

    export_tarball(
        api,
        # Verbose output helps avoid a buildbot timeout when no output
        # is produced for a long time.
        [
            '--remove-nonessential-files',
            'chromium-%s' % version, '--verbose', '--progress', '--src-dir',
            dest_dir
        ],
        'chromium-%s.tar.xz' % version,
        'chromium-%s-nacl.tar.xz' % version)


@recipe_api.composite_step
def fetch_pgo_profiles(api):
  pgo_script_path = api.path['checkout'].join('tools', 'update_pgo_profiles.py')
  pgo_script_args = [
      '--target=linux', 'update',
      '--gs-url-base=chromium-optimization-profiles/pgo_profiles'
  ]
  api.python('fetch Linux PGO profiles', pgo_script_path, pgo_script_args)


@recipe_api.composite_step
def fetch_afdo_profile(api):
  android_profile_path = api.path['checkout'].join('chrome', 'android',
                                                   'profiles')
  afdo_script_path = api.path['checkout'].join(
      'tools', 'download_optimization_profile.py')
  afdo_script_args = [
      '--newest_state',
      android_profile_path.join('newest.txt'), '--local_state',
      android_profile_path.join('local.txt'), '--output_name',
      android_profile_path.join('afdo.prof'),
      '--gs_url_base=chromeos-prebuilt/afdo-job/llvm'
  ]
  api.python('fetch android AFDO profile', afdo_script_path, afdo_script_args)


def trigger_publish_tarball_jobs(api):
  ls_result = api.gsutil(['ls', 'gs://chromium-browser-official/'],
                         stdout=api.raw_io.output()).stdout
  missing_releases = set()
  # TODO(phajdan.jr): find better solution than hardcoding version number.
  # We do that currently (carryover from a solution this recipe is replacing)
  # to avoid running into errors with older releases.
  # Exclude ios - it often uses internal buildspecs so public ones don't work.
  for release in api.omahaproxy.history(
      min_major_version=74, exclude_platforms=['ios']):
    if release['channel'] not in ('stable', 'beta', 'dev', 'canary'):
      continue
    version = release['version']
    if not published_all_tarballs(version, ls_result):
      missing_releases.add(version)
  for version in missing_releases:
    if version not in BLACKLISTED_VERSIONS:
      api.scheduler.emit_trigger(
          api.scheduler.BuildbucketTrigger(properties={'version': version}),
          project='infra',
          jobs=['publish_tarball'])


def publish_tarball(api):
  version = api.properties['version']

  ls_result = api.gsutil(['ls', 'gs://chromium-browser-official/'],
                         stdout=api.raw_io.output()).stdout
  if published_all_tarballs(version, ls_result):
    return

  api.gclient.set_config('chromium')
  solution = api.gclient.c.solutions[0]
  solution.revision = 'refs/tags/%s' % version
  api.bot_update.ensure_checkout(
      with_branch_heads=True, with_tags=True, suffix=version)

  api.git('clean', '-dffx')
  with api.context(cwd=api.path['checkout']):
    api.gclient(
        'sync',
        ['sync', '-D', '--nohooks', '--with_branch_heads', '--with_tags'])

  api.step('touch chrome/test/data/webui/i18n_process_css_test.html', [
      'touch', api.path['checkout'].join('chrome', 'test', 'data', 'webui',
                                         'i18n_process_css_test.html')
  ])

  api.python('Generate LASTCHANGE',
             api.path['checkout'].join('build', 'util', 'lastchange.py'),
             ['-o', api.path['checkout'].join('build', 'util', 'LASTCHANGE')])

  api.file.copy(
      'copy clang-format', api.chromium.resource('clang-format'),
      api.path['checkout'].join('buildtools', 'linux64', 'clang-format'))

  update_script = 'build.py'
  update_args = [
      '--without-android', '--use-system-cmake', '--gcc-toolchain=/usr',
      '--skip-build', '--without-fuchsia'
  ]
  api.step(
      'download clang sources',
      [api.path['checkout'].join('tools', 'clang', 'scripts', update_script)] +
      update_args)

  if [int(x) for x in version.split('.')] >= [87, 0, 4273, 0]:
    fetch_pgo_profiles(api)
  else:
    fetch_afdo_profile(api)

  node_modules_sha_path = api.path['checkout'].join('third_party', 'node',
                                                    'node_modules.tar.gz.sha1')
  if api.path.exists(node_modules_sha_path):
    api.python('webui_node_modules',
               api.depot_tools.download_from_google_storage_path, [
                   '--no_resume',
                   '--extract',
                   '--no_auth',
                   '--bucket',
                   'chromium-nodejs',
                   '-s',
                   node_modules_sha_path,
               ])

  try:
    temp_dir = api.path.mkdtemp('gn')
    git_root = temp_dir.join('gn')
    api.step('checkout gn',
             ['git', 'clone', 'https://gn.googlesource.com/gn', git_root])

    # Check out the same version of gn as the one pulled down from gclient.
    result = api.step(
        'get gn version',
        [api.path['checkout'].join('buildtools', 'linux64', 'gn'), '--version'],
        stdout=api.raw_io.output())
    match = re.match(r'\d+ \((.+)\)$', result.stdout.strip())
    commit = match.group(1)
    api.step('checkout gn commit', ['git', '-C', git_root, 'checkout', commit])

    tools_gn = api.path['checkout'].join('tools', 'gn')
    api.python('generate last_commit_position.h',
               git_root.join('build', 'gen.py'))
    api.file.remove('rm README.md', tools_gn.join('README.md'))
    for f in api.file.listdir(
        'listdir gn', git_root, test_data=['build', '.git']):
      basename = api.path.basename(f)
      if basename not in ['.git', '.gitignore', '.linux-sysroot', 'out']:
        api.file.move('move gn ' + basename, f, tools_gn.join(basename))
    api.file.move('move last_commit_position.h',
                  git_root.join('out', 'last_commit_position.h'),
                  tools_gn.join('bootstrap', 'last_commit_position.h'))
  finally:
    api.file.rmtree('rmtree temp dir', temp_dir)

  with api.step.defer_results():
    if not published_full_tarball(version, ls_result):
      export_tarball(
          api,
          # Verbose output helps avoid a buildbot timeout when no output
          # is produced for a long time.
          [
              '--remove-nonessential-files',
              'chromium-%s' % version, '--verbose', '--progress', '--src-dir',
              api.path['checkout']
          ],
          'chromium-%s.tar.xz' % version,
          'chromium-%s.tar.xz' % version)

      # Trigger a tarball build now that the full tarball has been uploaded.
      api.scheduler.emit_trigger(
          api.scheduler.BuildbucketTrigger(properties={'version': version}),
          project='infra',
          jobs=['Build From Tarball'],
      )

    if not published_test_tarball(version, ls_result):
      export_tarball(
          api,
          # Verbose output helps avoid a buildbot timeout when no output
          # is produced for a long time.
          [
              '--test-data',
              'chromium-%s' % version, '--verbose', '--progress', '--src-dir',
              api.path['checkout']
          ],
          'chromium-%s.tar.xz' % version,
          'chromium-%s-testdata.tar.xz' % version)

    if not published_lite_tarball(version, ls_result):
      export_lite_tarball(api, version)

    if not published_nacl_tarball(version, ls_result):
      export_nacl_tarball(api, version)


def RunSteps(api):
  if 'version' not in api.properties:
    # This code path executes on 'publish_tarball_dispatcher' builder.
    trigger_publish_tarball_jobs(api)
  else:
    # This code path executes on 'publish_tarball' builder.
    publish_tarball(api)


def GenTests(api):
  yield (api.test('basic') + api.buildbucket.generic_build() +
         api.properties(version='87.0.4273.0') + api.platform('linux', 64) +
         api.step_data('gsutil ls', stdout=api.raw_io.output('')) +
         api.step_data(
             'get gn version', stdout=api.raw_io.output('1496 (0790d304)')) +
         api.path.exists(api.path['checkout'].join('third_party', 'node',
                                                   'node_modules.tar.gz.sha1')))

  yield (api.test('dupe') + api.buildbucket.generic_build() + api.properties(
      version='74.0.3729.169'
  ) + api.platform('linux', 64) + api.step_data(
      'gsutil ls',
      stdout=api.raw_io.output(
          'gs://chromium-browser-official/chromium-74.0.3729.169.tar.xz\n'
          'gs://chromium-browser-official/chromium-74.0.3729.169-lite.tar.xz\n'
          'gs://chromium-browser-official/'
          'chromium-74.0.3729.169-testdata.tar.xz\n'
          'gs://chromium-browser-official/chromium-74.0.3729.169-nacl.tar.xz\n')
  ))

  yield (api.test('clang-no-fuchsia') + api.buildbucket.generic_build() +
         api.properties(version='74.0.3729.169') + api.platform('linux', 64) +
         api.step_data('gsutil ls', stdout=api.raw_io.output('')) +
         api.step_data(
             'get gn version', stdout=api.raw_io.output('1496 (0790d304)')) +
         api.path.exists(api.path['checkout'].join('third_party', 'node',
                                                   'node_modules.tar.gz.sha1')))

  # This can be removed once M87 becomes stable.
  yield (api.test('afdo-old-script') + api.buildbucket.generic_build() +
         api.properties(version='85.0.4125.0') + api.platform('linux', 64) +
         api.step_data('gsutil ls', stdout=api.raw_io.output('')) +
         api.step_data(
             'get gn version', stdout=api.raw_io.output('1496 (0790d304)')) +
         api.path.exists(api.path['checkout'].join(
             'third_party', 'node', 'node_modules.tar.gz.sha1')) +
         api.path.exists(api.path['checkout'].join(
             'tools', 'download_cros_provided_profile.py')))

  yield (api.test('trigger') + api.buildbucket.generic_build() +
         api.platform('linux', 64) +
         api.step_data('gsutil ls', stdout=api.raw_io.output('')))

  yield (
      api.test('basic-m76') + api.buildbucket.generic_build() +
      api.properties(version='76.0.3784.0') + api.platform('linux', 64) +
      api.post_process(post_process.StepCommandRE, 'download clang sources', [
          '.*/build.py', '--without-android', '--use-system-cmake',
          '--gcc-toolchain=/usr', '--skip-build', '--without-fuchsia'
      ]) + api.post_process(post_process.DropExpectation) + api.step_data(
          'get gn version', stdout=api.raw_io.output('1496 (0790d304)')) +
      api.step_data(
          'gsutil ls',
          stdout=api.raw_io.output(
              'gs://chromium-browser-official/chromium-74.0.3729.169.tar.xz\n'
              'gs://chromium-browser-official/'
              'chromium-74.0.3729.169-lite.tar.xz\n'
              'gs://chromium-browser-official/'
              'chromium-74.0.3729.169-nacl.tar.xz\n')))
