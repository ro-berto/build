# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for archiving officially tagged v8 builds.
"""

import re

from recipe_engine.config import Single
from recipe_engine.post_process import (
    DoesNotRun, DropExpectation, Filter, MustRun, StatusFailure)
from recipe_engine.recipe_api import Property

DEPS = [
  'chromium',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/gsutil',
  'gn',
  'recipe_engine/buildbucket',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'v8',
  'zip',
]


PROPERTIES = {
  # One of Release|Debug.
  'build_config': Property(default=None, kind=str),
  # One of intel|arm|mips.
  'target_arch': Property(default=None, kind=str),
  # One of 32|64.
  'target_bits': Property(default=None, kind=Single((int, float))),
  # One of android|fuchsia|linux|mac|win.
  'target_platform': Property(default=None, kind=str),
}

ARCHIVE_LINK = 'https://storage.googleapis.com/chromium-v8/official/%s/%s'
BRANCH_RE = re.compile(r'^refs/(branch-heads/\d+\.\d+|heads/\d+\.\d+\.\d+)$')
RELEASE_BRANCH_RE = re.compile(r'^(?:refs/branch-heads/)?(\d+\.\d+)$')
FIRST_BUILD_IN_MILESTONE_RE = re.compile(r'^\d+\.\d+\.\d+$')


def make_archive(api, bot_config, ref, version, archive_type, step_suffix='',
                 archive_suffix=''):
  with api.step.nest('sync' + step_suffix):
    api.v8.apply_bot_config(bot_config)
    if archive_type == 'ref':
      api.chromium.c.gn_args.append('is_official_build=true')
    api.chromium.apply_config('clobber')
    api.chromium.apply_config('default_target_v8_archive')
    if api.chromium.c.build_config_fs == 'Debug':
      api.chromium.apply_config('slow_dchecks')
    elif archive_type in ['all', 'lib']:
      api.chromium.apply_config('v8_static_library')
    if api.chromium.c.TARGET_PLATFORM == 'android':
      api.chromium.apply_config('v8_android')
    elif api.chromium.c.TARGET_ARCH == 'arm':
      api.chromium.apply_config('arm_hard_float')

    # Opt out of using gyp environment variables.
    api.chromium.c.use_gyp_env = False
    api.v8.checkout()

    if not version:
      version = str(api.v8.read_version_from_ref(api.v8.revision, 'head'))
      tags = set(x.strip() for x in api.git(
          'describe', '--tags', 'HEAD',
          stdout=api.raw_io.output_text(),
      ).stdout.strip().splitlines())

      if version not in tags:
        api.step('Skipping due to missing tag.', cmd=None)
        return None, None

    # This automatically deletes build_dir since we specify clobber above.
    api.v8.runhooks()

  build_dir = api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)
  with api.step.nest('build' + step_suffix):
    compile_failure = api.v8.compile()
    if compile_failure:
      return None, compile_failure

  with api.step.nest('make archive' + step_suffix) as parent:
    # Make a list of files to archive.
    file_list_test_data = map(str, map(build_dir.join, ['d8', 'icudtl.dat']))
    file_list = api.python(
        'filter build files',
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
    package.zip('zipping')

    if api.chromium.c.TARGET_ARCH != 'intel':
      # Only disambiguate non-intel architectures. This is closest to our naming
      # conventions.
      arch_name = '-%s' % api.chromium.c.TARGET_ARCH
    else:
      arch_name = ''

    # Upload refbuild and trigger refbuild bundler.
    if archive_type == 'ref':
      platform = '%s%s%s%s' % (api.chromium.c.TARGET_PLATFORM, arch_name,
                               api.chromium.c.TARGET_BITS, archive_suffix)
      api.gsutil.upload(
          zip_file,
          'chromium-v8/official/refbuild',
          'v8-%s-rel.zip' % platform,
          args=['-a', 'public-read'],
          name='update refbuild binaries',
      )
      api.v8.buildbucket_trigger(
          [('v8_refbuild_bundler', {
              'revision': api.v8.revision,
              'platform': platform,
          })],
          project='v8-internal',
          bucket='ci',
          step_name='trigger refbuild bundler')
      return None, None

    # Upload to google storage bucket.
    build_config = 'rel' if api.chromium.c.BUILD_CONFIG == 'Release' else 'dbg'
    archive_prefix = (
        'v8-%s%s%s%s-%s' %
        (api.chromium.c.TARGET_PLATFORM, arch_name, api.chromium.c.TARGET_BITS,
        archive_suffix, build_config)
    )
    archive_name = '%s-%s.zip' % (archive_prefix, version)
    branch_match = RELEASE_BRANCH_RE.match(ref)
    gs_path_suffix = branch_match.group(1) if branch_match else 'canary'
    gs_path = 'chromium-v8/official/%s' % gs_path_suffix
    api.gsutil.upload(
        zip_file,
        gs_path,
        archive_name,
        args=['-a', 'public-read'],
        name='upload',
    )

    if gs_path_suffix == 'canary':
      api.gsutil.upload(
          api.json.input({'version': version}),
          gs_path,
          '%s-latest.json' % archive_prefix,
          args=['-a', 'public-read'],
          name='upload json',
      )

    parent.presentation.links['download'] = (
        ARCHIVE_LINK % (gs_path_suffix, archive_name))
    return version, None


def RunSteps(api, build_config, target_arch, target_bits, target_platform):
  target_bits = int(target_bits)

  with api.step.nest('initialization'):
    # Ensure a proper branch is specified.
    ref = api.buildbucket.gitiles_commit.ref
    if not ref or not BRANCH_RE.match(ref):
      api.step('Skipping due to missing release branch.', cmd=None)
      return

    # Apply properties from cr-buildbucket.cfg.
    bot_config = {
      'chromium_apply_config': [
        'default_compiler', 'goma', 'gn'],
      'v8_config_kwargs': {},
    }
    for key, value in (
        ('BUILD_CONFIG', build_config),
        ('TARGET_ARCH', target_arch),
        ('TARGET_BITS', target_bits),
        ('TARGET_PLATFORM', target_platform)):
      if value:
        bot_config['v8_config_kwargs'][key] = value

  if build_config == 'Debug':
    # Debug binaries require libraries to be present in the same archive to run.
    version, compile_failure = make_archive(api, bot_config, ref, None, 'all')
    if compile_failure:
      return compile_failure
  else:
    version, compile_failure = make_archive(api, bot_config, ref, None, 'exe')
    if compile_failure:
      return compile_failure
    if not version:
      return
    version, compile_failure = make_archive(
        api, bot_config, ref, version, 'lib', ' (libs)', '-libs')
    if compile_failure:
      return compile_failure

    # Upload first build for the latest milestone to a known location. We use
    # these binaries for running reference perf tests.
    if (RELEASE_BRANCH_RE.match(ref) and
        FIRST_BUILD_IN_MILESTONE_RE.match(version)):
      version, compile_failure = make_archive(
          api, bot_config, ref, version, 'ref', ' (ref)')
      if compile_failure:
        return compile_failure


def GenTests(api):
  def test_defaults(name, platform, build_config, **kwargs):
    return api.test(
        api.v8.test_name('client.v8.official', 'V8 Foobar', name),
        api.properties.generic(
            mastername='client.v8.official',
            path_config='generic',
            build_config=build_config,
            **kwargs),
        api.buildbucket.ci_build(
            project='v8',
            git_repo='https://chromium.googlesource.com/v8/v8',
            builder='V8 Foobar',
            git_ref='refs/branch-heads/3.4',
            revision='a' * 40),
        api.platform(platform, 64),
        api.v8.version_file(17, 'head', prefix='sync.'),
        api.override_step_data('sync.git describe',
                               api.raw_io.stream_output('3.4.3.17')),
        api.v8.check_param_equals(
            'sync.bot_update', '--revision', 'v8@refs/branch-heads/' +
            '3.4:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
        api.runtime(is_luci=True, is_experimental=False),
        api.post_process(MustRun, 'sync.clobber', 'sync.gclient runhooks',
                         'build.gn', 'build.compile', 'make archive.zipping',
                         'make archive.gsutil upload'),
    )

  def filter_steps(is_release):
    expected_steps = [
        'build.gn', 'build.compile', 'make archive',
        'make archive.filter build files', 'make archive.zipping',
        'make archive.gsutil upload',
    ]
    if is_release:
      expected_steps.extend([
        'build (libs)', 'build (libs).gn', 'build (libs).compile',
        'make archive (libs)', 'make archive (libs).filter build files',
        'make archive (libs).zipping', 'make archive (libs).gsutil upload',
      ])

    return api.post_process(Filter(*expected_steps))

  # Test standard run on linux.
  yield (
      test_defaults('linux', 'linux', build_config='Debug', target_bits=64) +
      filter_steps(is_release=False)
  )

  # Test Android-specific things.
  yield (
      test_defaults(
          'android', 'linux', build_config='Release',
          target_arch='arm', target_bits=64, target_platform='android') +
      # Make sure bot_update specifies target_os on Android builders.
      api.v8.check_in_param(
          'sync.bot_update', '--spec-path',
          'target_os = [\'android\']') +
      filter_steps(is_release=True)
  )

  # Test Arm-specific things.
  yield (
      test_defaults(
          'arm', 'linux', build_config='Release',
          target_arch='arm', target_bits=32) +
      # Make sure bot_update specifies target_cpu on Arm builders.
      api.v8.check_in_param(
          'sync.bot_update', '--spec-path',
          'target_cpu = [\'arm\', \'arm64\']') +
      filter_steps(is_release=True)
  )

  # Test Windows-specific things.
  yield (
      test_defaults(
          'windows', 'win', build_config='Release', target_bits=64) +
      # Check that _x64 suffix is correctly removed on windows.
      api.v8.check_param_equals(
          'make archive.filter build files',
          '--dir',
          '[BUILDER_CACHE]\\v8\\out\\Release') +
      # Show GN configs to be resiliant to changes of chromium configs.
      api.post_process(Filter('build.gn'))
  )

  # Test Mac-specific things.
  yield (
      test_defaults(
          'mac', 'mac', build_config='Release', target_bits=64) +
      # Show GN configs to be resiliant to changes of chromium configs.
      api.post_process(Filter('build.gn'))
  )

  # Test bailout on missing branch.
  mastername = 'client.v8.official'
  buildername = 'V8 Foobar'
  yield api.test(
      api.v8.test_name(mastername, buildername, 'no_branch'),
      api.properties.generic(
          mastername=mastername,
          path_config='generic',
          build_config='Release',
          target_bits=64),
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder=buildername,
          revision='a' * 40,
      ),
      api.post_process(
          MustRun, 'initialization.Skipping due to missing release branch.'),
      api.post_process(DoesNotRun, 'sync.gclient runhooks', 'build.gn',
                       'build.compile', 'make archive.zipping',
                       'make archive.gsutil upload'),
      api.runtime(is_luci=True, is_experimental=False),
      api.post_process(DropExpectation),
  )

  # Test bailout on missing tag.
  mastername = 'client.v8.official'
  buildername = 'V8 Foobar'
  yield api.test(
      api.v8.test_name(mastername, buildername, 'no_tag'),
      api.properties.generic(
          mastername=mastername,
          path_config='generic',
          build_config='Release',
          target_bits=64),
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder=buildername,
          git_ref='refs/branch-heads/3.4',
          revision='a' * 40,
      ),
      api.v8.version_file(17, 'head', prefix='sync.'),
      api.override_step_data('sync.git describe',
                             api.raw_io.stream_output('3.4.3.17-blabla')),
      api.post_process(MustRun, 'sync.Skipping due to missing tag.'),
      api.post_process(DoesNotRun, 'sync.gclient runhooks', 'build.gn',
                       'build.compile', 'make archive.zipping',
                       'make archive.gsutil upload'),
      api.runtime(is_luci=True, is_experimental=False),
      api.post_process(DropExpectation),
  )

  # Test refbuilds.
  mastername = 'client.v8.official'
  buildername = 'V8 Foobar'
  yield api.test(
      api.v8.test_name(mastername, buildername, 'update_beta'),
      api.properties.generic(
          mastername=mastername,
          path_config='generic',
          build_config='Release',
          target_bits=64),
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder=buildername,
          git_ref='refs/branch-heads/3.4',
          revision='a' * 40,
      ),
      api.v8.version_file(0, 'head', prefix='sync.'),
      api.override_step_data('sync.git describe',
                             api.raw_io.stream_output('3.4.3')),
      api.runtime(is_luci=True, is_experimental=False),
      api.post_process(Filter().include_re('.*ref.*')),
  )

  # Test canary upload.
  mastername = 'client.v8.official'
  buildername = 'V8 Foobar'
  yield api.test(
      api.v8.test_name(mastername, buildername, 'canary'),
      api.properties.generic(
          mastername=mastername,
          path_config='generic',
          build_config='Release',
          target_bits=64),
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder=buildername,
          git_ref='refs/heads/3.4.3',
          revision='a' * 40,
      ),
      api.v8.version_file(1, 'head', prefix='sync.'),
      api.override_step_data('sync.git describe',
                             api.raw_io.stream_output('3.4.3.1')),
      api.runtime(is_luci=True, is_experimental=False),
      api.post_process(
          Filter(
              'make archive.gsutil upload',
              'make archive.gsutil upload json',
          )),
  )

  # Test coverage for compile failures
  yield api.test(
      api.v8.test_name('client.v8.official', 'V8 Foobar',
                       'debug_compile_failure'),
      api.properties.generic(
          mastername='client.v8.official',
          path_config='generic',
          build_config='Debug',
          target_bits=64),
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder='V8 Foobar',
          git_ref='refs/branch-heads/3.4',
          revision='a' * 40),
      api.platform('linux', 64),
      api.v8.version_file(17, 'head', prefix='sync.'),
      api.override_step_data('sync.git describe',
                             api.raw_io.stream_output('3.4.3.17')),
      api.v8.check_param_equals(
          'sync.bot_update', '--revision', 'v8@refs/branch-heads/' +
          '3.4:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
      api.runtime(is_luci=True, is_experimental=False),
      api.step_data('build.compile', retcode=1),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

  yield api.test(
      api.v8.test_name('client.v8.official', 'V8 Foobar',
                       'release_compile_failure'),
      api.properties.generic(
          mastername='client.v8.official',
          path_config='generic',
          build_config='Release',
          target_bits=64),
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder='V8 Foobar',
          git_ref='refs/branch-heads/3.4',
          revision='a' * 40),
      api.platform('linux', 64),
      api.v8.version_file(17, 'head', prefix='sync.'),
      api.override_step_data('sync.git describe',
                             api.raw_io.stream_output('3.4.3.17')),
      api.v8.check_param_equals(
          'sync.bot_update', '--revision', 'v8@refs/branch-heads/' +
          '3.4:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
      api.runtime(is_luci=True, is_experimental=False),
      api.step_data('build.compile', retcode=1),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

  yield api.test(
      api.v8.test_name('client.v8.official', 'V8 Foobar',
                       'release_libs_compile_failure'),
      api.properties.generic(
          mastername='client.v8.official',
          path_config='generic',
          build_config='Release',
          target_bits=64),
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder='V8 Foobar',
          git_ref='refs/branch-heads/3.4',
          revision='a' * 40),
      api.platform('linux', 64),
      api.v8.version_file(17, 'head', prefix='sync.'),
      api.override_step_data('sync.git describe',
                             api.raw_io.stream_output('3.4.3.17')),
      api.v8.check_param_equals(
          'sync.bot_update', '--revision', 'v8@refs/branch-heads/' +
          '3.4:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
      api.runtime(is_luci=True, is_experimental=False),
      api.step_data('build (libs).compile', retcode=1),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

  yield api.test(
      api.v8.test_name('client.v8.official', 'V8 Foobar',
                       'milestone_compile_failure'),
      api.properties.generic(
          mastername=mastername,
          path_config='generic',
          build_config='Release',
          target_bits=64),
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder=buildername,
          git_ref='refs/branch-heads/3.4',
          revision='a' * 40,
      ),
      api.v8.version_file(0, 'head', prefix='sync.'),
      api.override_step_data('sync.git describe',
                             api.raw_io.stream_output('3.4.3')),
      api.step_data('build (ref).compile', retcode=1),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )
