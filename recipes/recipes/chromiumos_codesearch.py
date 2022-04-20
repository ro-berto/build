# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe for enabling cross-references in code search for ChromiumOS.

Checks out and builds ChromiumOS for amd64-generic, does some preprocessing for
package_index, and generates then uploads a KZIP to GS.
"""

from recipe_engine import config
from recipe_engine.engine_types import freeze
from recipe_engine.post_process import StepCommandRE, DropExpectation
from recipe_engine.recipe_api import Property

PYTHON_VERSION_COMPATIBILITY = 'PY3'

DEPS = [
    'codesearch',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/gsutil',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
    'recipe_engine/time',
    'recipe_engine/raw_io',
]

# TODO(crbug/1284439): Add build_config.
# TODO(crbug/1317852): Move properties outside of recipe.
SPEC = freeze({
    # The builders have the following parameters:
    # - board: the compile targets.
    # - corpus: Kythe corpus to specify in the kzip.
    # - packages: The platform for which the code is compiled.
    # - sync_generated_files: Whether to sync generated files into a git repo.
    # - experimental: Whether to mark Kythe uploads as experimental.
    'builders': {
        'codesearch-gen-chromiumos-amd64-generic': {
            'board': 'amd64-generic',
            'corpus': 'chromium.googlesource.com/chromiumos/codesearch//main',
            'packages': [
                'virtual/target-chromium-os',
                'virtual/target-chromium-os-dev',
                'virtual/target-chromium-os-factory',
                'virtual/target-chromium-os-factory-shim',
                'virtual/target-chromium-os-test',
            ],
            # TODO(crbug/1284439): Set sync_generated_files to True and
            # configure syncing of chroot and out dirs.
            'sync_generated_files': False,
            'experimental': False,
        },
    },
})

# TODO(crbug/1284439): Replace timestamp with annealing manifest snapshot.
PROPERTIES = {
    'codesearch_mirror_revision':
        Property(
            kind=str,
            help='The revision for codesearch to use for kythe references.',
            default=None),
    'codesearch_mirror_revision_timestamp':
        Property(
            kind=str,
            help='The commit timestamp of the revision for codesearch to use, '
            'in seconds since the UNIX epoch.',
            default=None),
}


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


def RunSteps(api, codesearch_mirror_revision,
             codesearch_mirror_revision_timestamp):
  builder = api.buildbucket.build.builder.builder
  bot_config = SPEC.get('builders', {}).get(builder)
  assert bot_config is not None, ('Could not find builder %s in SPEC' % builder)

  board = bot_config.get('board', 'amd64-generic')
  corpus = bot_config.get(
      'corpus', 'chromium.googlesource.com/chromiumos/codesearch//main')
  packages = bot_config.get('packages', ['virtual/target-chromium-os'])
  sync_generated_files = bot_config.get('sync_generated_files', False)
  experimental = bot_config.get('experimental', False)

  # Get infra/infra. Checking out infra automatically checks out depot_tools.
  cache_dir = api.path['cache'].join('builder')
  with api.context(cwd=cache_dir):
    api.bot_update.ensure_checkout(
        gclient_config=gclient_config(api), set_output_commit=False)
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
        '--with-tests',
        '--build-dir',
        build_dir,
        '--gn-targets',
        build_dir.join('gn_targets.json'),
        '--compile-commands',
        build_dir.join('compile_commands.json'),
    ] + list(packages))

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
      commit_hash=codesearch_mirror_revision,
      commit_timestamp=int(codesearch_mirror_revision_timestamp or
                           api.time.time()))


# TODO(crbug/1284439): Add more tests.
def GenTests(api):
  yield api.test(
      'basic',
      api.buildbucket.generic_build(
          builder='codesearch-gen-chromiumos-amd64-generic'),
      api.step_data('repo init'),
      api.properties(
          codesearch_mirror_revision='a' * 40,
          codesearch_mirror_revision_timestamp='1531887759'))

  yield api.test(
      'repo sync to ToT',
      api.buildbucket.generic_build(
          builder='codesearch-gen-chromiumos-amd64-generic'),
      api.step_data('repo init'), api.step_data('repo sync'),
      api.properties(
          codesearch_mirror_revision='a' * 40,
          codesearch_mirror_revision_timestamp='1531887759'),
      api.post_process(StepCommandRE, 'repo sync', ['.*repo', 'sync', '-j6']),
      api.post_process(DropExpectation))
