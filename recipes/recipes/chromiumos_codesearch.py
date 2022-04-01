# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe for enabling cross-references in code search for ChromiumOS.

Checks out and builds ChromiumOS for amd64-generic, does some preprocessing for
package_index, and generates then uploads a KZIP to GS.

TODO(crbug/1284439): Create an initiator recipe that triggers builds for
multiple boards.
"""

PYTHON_VERSION_COMPATIBILITY = 'PY3'

DEPS = [
    'codesearch',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/gsutil',
    'depot_tools/tryserver',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/step',
    'recipe_engine/time',
    'recipe_engine/raw_io',
]

SOURCE_REPO = 'https://chromium.googlesource.com/chromiumos/codesearch'


def gclient_config(api):
  """Generate a gclient configuration to check out infra/infra.

  Return: (config) A gclient recipe module configuration.
  """
  cfg = api.gclient.make_config()
  soln = cfg.solutions.add()
  soln.name = 'infra'
  soln.url = 'https://chromium.googlesource.com/infra/infra'
  soln.revision = 'HEAD'
  return cfg


def get_mirror_hash_and_timestamp(api, checkout_dir):
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
  return mirror_hash, mirror_unix_timestamp


def RunSteps(api):
  # TODO(crbug/1284439): Parametrize this when using initiator recipe.
  board = 'amd64-generic'
  experimental = False
  sync_generated_files = False
  corpus = 'chromium.googlesource.com/chromiumos/codesearch//main'
  packages = [
      'virtual/target-chromium-os',
      'virtual/target-chromium-os-dev',
      'virtual/target-chromium-os-factory',
      'virtual/target-chromium-os-factory-shim',
      'virtual/target-chromium-os-test',
  ]

  # Get infra/infra. Checking out infra automatically checks out depot_tools.
  cache_dir = api.path['cache'].join('builder')
  with api.context(cwd=cache_dir):
    api.bot_update.ensure_checkout(gclient_config=gclient_config(api))

  # Get the hash and timestamp of the mirror repo before repo sync.
  mirror_hash, mirror_unix_timestamp = get_mirror_hash_and_timestamp(
      api, cache_dir)

  depot_tools_dir = cache_dir.join('depot_tools')

  # Set up and build ChromiumOS.
  # TODO(crbug/1284439): Add sentinel file and handle cleaning up chroot.
  # TODO(crbug/1284439): Investigate cros_sdk ImportError failures.
  chromiumos_dir = cache_dir.join('chromiumos')
  api.file.ensure_directory('ensure chromiumos dir', chromiumos_dir)
  with api.context(cwd=chromiumos_dir, env={'DEPOT_TOOLS_UPDATE': 0}):
    repo = depot_tools_dir.join('repo')
    if not api.file.glob_paths(
        'Check for existing checkout',
        chromiumos_dir,
        '.repo',
        include_hidden=True):
      api.step('repo init', [
          repo, 'init', '-u',
          'https://chromium.googlesource.com/chromiumos/manifest.git'
      ])
    api.step('repo sync', [repo, 'sync', '-j6'])

    cros_sdk = depot_tools_dir.join('cros_sdk')
    api.step('cros_sdk', [cros_sdk])
    api.step('setup_board',
             [cros_sdk, '--', 'setup_board',
              '--board=%s' % board])
    api.step('build_packages',
             [cros_sdk, '--', 'build_packages',
              '--board=%s' % board])

  # package_index_cros requires chromite/ in a parent directory.
  chromiumos_scripts_dir = chromiumos_dir.join('src', 'scripts')
  package_index_cros_dir = chromiumos_scripts_dir.join('package_index_cros')
  api.step('copy package_index_cros to chromiumos/src/scripts', [
      'cp', '-r',
      cache_dir.join('infra', 'go', 'src', 'infra', 'cmd',
                     'package_index_cros'), chromiumos_scripts_dir
  ])

  # Run package_index_cros and other preprocessing steps before generating KZIP.
  build_dir = chromiumos_dir.join('src', 'out', board)
  with api.context(
      cwd=chromiumos_scripts_dir,
      env={'PATH': api.path.pathsep.join([str(depot_tools_dir), '%(PATH)s'])}):
    api.step('run package_index_cros', [
        'python3',
        package_index_cros_dir.join('main.py'),
        '--with-build',
        '--build-dir',
        build_dir,
        '--gn-targets',
        build_dir.join('gn_targets.json'),
        '--compile-commands',
        build_dir.join('compile_commands.json'),
    ] + packages)

  # The codesearch recipe module relies on checkout path to be set.
  chromiumos_src_dir = chromiumos_dir.join('src')
  api.path['checkout'] = chromiumos_src_dir
  api.codesearch.set_config(
      'chromiumos',
      PROJECT='chromiumos',
      CHECKOUT_PATH=chromiumos_src_dir,
      PLATFORM=board,
      EXPERIMENTAL=experimental,
      SYNC_GENERATED_FILES=sync_generated_files,
      CORPUS=corpus,
  )

  # Download chromium clang tools.
  clang_dir = api.codesearch.clone_clang_tools(cache_dir)

  # Run the translation_unit tool in chromiumos/src dirs.
  api.codesearch.run_clang_tool(
      clang_dir=clang_dir,
      run_dirs=[
          chromiumos_src_dir.join('platform2'),
          chromiumos_src_dir.join('aosp', 'external', 'libchrome'),
          chromiumos_src_dir.join('aosp', 'system', 'update_engine'),
      ])

  # Create the kythe index pack and upload it to google storage.
  api.codesearch.create_and_upload_kythe_index_pack(
      commit_hash=mirror_hash,
      commit_timestamp=int(mirror_unix_timestamp or api.time.time()))


def GenTests(api):
  yield api.test(
      'basic',
      api.step_data('fetch mirror hash',
                    api.raw_io.stream_output_text('a' * 40, stream='stdout')),
      api.step_data('fetch mirror timestamp',
                    api.raw_io.stream_output_text('100', stream='stdout')),
      api.step_data('repo init'),
      api.step_data('repo sync'),
  )
