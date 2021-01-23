# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.recipes.build import chromium_3pp

DEPS = [
    'chromium',
    'chromium_checkout',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/tryserver',
    'infra/support_3pp',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

PROPERTIES = chromium_3pp.InputProperties


def RunSteps(api, properties):
  api.gclient.set_config('chromium')
  api.chromium_checkout.ensure_checkout()
  chromium_src = api.path['checkout']

  if properties.package_prefix:
    # Cast package_prefix to str since its type is unicode, but
    # set_package_prefix expects a str
    api.support_3pp.set_package_prefix(str(properties.package_prefix))
  api.support_3pp.set_source_cache_prefix('3pp_sources')

  package_paths_to_build = set(properties.package_paths_to_build)

  if api.tryserver.is_tryserver:
    api.support_3pp.set_experimental(True)

    # Analyze if the patch contains 3pp related changes and return early if not.
    with api.context(cwd=chromium_src):
      # Files from patch are under staged state so use "--cached" to only show
      # the staged changes.
      staged_diff_result = api.git(
          'diff',
          '--diff-filter=d',  # exclude deleted paths
          '--name-only',
          '--cached',
          name='Analyze',
          stdout=api.raw_io.output_text(add_output_log=True))
    file_paths = staged_diff_result.stdout.splitlines()
    for file_path in file_paths:
      file_dirs = file_path.split(api.path.sep)
      if '3pp' in file_dirs:
        index = file_dirs.index('3pp')
        package_paths_to_build.add(api.path.sep.join(file_dirs[:index]))

    if package_paths_to_build:
      staged_diff_result.presentation.logs['package_paths_to_build'] = sorted(
          package_paths_to_build)
    else:
      step_result = api.step('No 3pp related changes', cmd=None)
      return

  # Special steps for scripts that auto-generate 3pp PB files.
  # For third_party/android_deps/fetch_all.py
  api.step('Preprocessing third_party/android_deps', [
      chromium_src.join('third_party', 'android_deps', 'fetch_all.py'), '-v',
      '--ignore-vulnerabilities'
  ])

  # TODO: Migrate third_party/androidx/fetch_all_androidx.py.

  # Fail if there are unexpected (i.e. not part of the CL under test) changes
  # related to 3pp.
  # This is to prevent the scripts above (e.g. fetch_all.py) from making
  # unexpected changes to 3pp files.
  with api.context(cwd=chromium_src):
    unstaged_diff_result = api.git(
        'diff',
        '--diff-filter=d',  # exclude deleted paths
        '--name-only',
        name='Confirm no-op',
        stdout=api.raw_io.output_text(add_output_log=True))

  unexpected_3pp_files = []
  for file_path in unstaged_diff_result.stdout.splitlines():
    if '3pp' in file_path.split(api.path.sep):
      unexpected_3pp_files.append(file_path)
  if unexpected_3pp_files:
    step_name = 'Unexpected 3pp changes'
    step_result = api.step(step_name, cmd=None)
    step_result.presentation.status = api.step.FAILURE
    step_result.presentation.step_text = '\n'.join(unexpected_3pp_files)
    raise api.step.StepFailure(step_name, step_result)

  with api.step.nest('Load all packages'):
    api.support_3pp.load_packages_from_path(
        chromium_src, glob_pattern='**/3pp/3pp.pb', check_dup=True)

  cipd_pkg_names_to_build = set()

  for package_path in package_paths_to_build:
    with api.step.nest('Load to-build packages from %s' % package_path):
      cipd_pkg_names_to_build.update(
          api.support_3pp.load_packages_from_path(
              chromium_src,
              glob_pattern='%s/%s' % (package_path.strip('/'), '3pp/3pp.pb'),
              check_dup=False))

  _, unsupported = api.support_3pp.ensure_uploaded(
      # Note that when empty, all known packages will be built.
      packages=cipd_pkg_names_to_build,
      platform=properties.platform,
      force_build=api.tryserver.is_tryserver or properties.force_build,
  )

  if unsupported:
    step_name = 'Unsupported packages'
    step_result = api.step(step_name, cmd=None)
    step_result.presentation.step_text = '\n'.join(unsupported)


def GenTests(api):
  yield api.test(
      'basic',
      api.properties(platform='linux-amd64', package_prefix='chromium'),
      api.post_process(
          post_process.MustRun,
          'Load all packages',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic_to_build',
      api.properties(
          package_paths_to_build=[
              'third_party/bar/some',
          ],
          platform='linux-amd64',
          package_prefix='chromium'),
      api.post_process(
          post_process.MustRun,
          'Load to-build packages from third_party/bar/some',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'unexpected_3pp_change',
      api.properties(
          platform='linux-amd64',
          package_prefix='chromium'),
      api.override_step_data(
          'Confirm no-op',
          api.raw_io.stream_output('third_party/qux/3pp/3pp.pb')),
      api.post_process(post_process.MustRun, 'Unexpected 3pp changes'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'unsupported_packages',
      api.properties(platform='linux-amd64', package_prefix='chromium'),
      api.override_step_data('Load all packages.find package specs',
                             api.file.glob_paths(['pear/3pp/3pp.pb'])),
      api.override_step_data(
          "Load all packages.load package specs."
          "read 'pear/3pp/3pp.pb'",
          api.file.read_text('''
              create { unsupported: true }
              upload { pkg_prefix: "prefix/deps" }
              ''')),
      api.post_process(post_process.StepTextEquals, 'Unsupported packages',
                       'prefix/deps/pear'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  # Tests for trybot
  trybot_basic_other = '''
  create {
    source { git {} }
  }
  upload {pkg_prefix: "p_apple"}
  '''
  trybot_basic_some = '''
  create {
    source { git {} }
  }
  upload {pkg_prefix: "p_apple"}
  '''
  yield api.test(
      'trybot_basic',
      api.chromium.try_build(),
      api.properties(
          package_paths_to_build=[
              'third_party/some',
          ],
          platform='linux-amd64',
          package_prefix='chromium'),
      api.override_step_data(
          'Analyze',
          api.raw_io.stream_output('third_party/other/3pp/fetch.py')),
      api.post_process(post_process.LogEquals, 'Analyze',
                       'package_paths_to_build',
                       '\n'.join(['third_party/other', 'third_party/some'])),
      api.override_step_data(
          'Load all packages.find package specs',
          api.file.glob_paths(
              ['third_party/other/3pp/3pp.pb', 'third_party/some/3pp/3pp.pb'])),
      api.override_step_data(
          "Load all packages.load package specs."
          "read 'third_party/other/3pp/3pp.pb'",
          api.file.read_text(trybot_basic_other)),
      api.override_step_data(
          "Load all packages.load package specs."
          "read 'third_party/some/3pp/3pp.pb'",
          api.file.read_text(trybot_basic_some)),
      api.override_step_data(
          'Load to-build packages from third_party/other.find package specs',
          api.file.glob_paths(['third_party/other/3pp/3pp.pb'])),
      api.override_step_data(
          "Load to-build packages from third_party/other.load package specs."
          "read 'third_party/other/3pp/3pp.pb'",
          api.file.read_text(trybot_basic_other)),
      api.override_step_data(
          'Load to-build packages from third_party/some.find package specs',
          api.file.glob_paths(['third_party/some/3pp/3pp.pb'])),
      api.override_step_data(
          "Load to-build packages from third_party/some.load package specs."
          "read 'third_party/some/3pp/3pp.pb'",
          api.file.read_text(trybot_basic_some)),
      api.post_process(post_process.MustRun, 'building p_apple/other',
                       'building p_apple/some'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'trybot_no_3pp_change',
      api.chromium.try_build(),
      api.override_step_data(
          'Analyze',
          api.raw_io.stream_output('\n'.join(
              ['foo.cc', 'testing/buildbot/bar.json']))),
      api.post_process(post_process.MustRun, 'No 3pp related changes'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
