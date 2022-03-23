# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe for enabling cross-references in code search for ChromiumOS.

Checks out and builds ChromiumOS for amd64-generic, does some preprocessing for
package_index, and generates then uploads a KZIP to GS.

TODO(crbug/1284439): Create an initiator recipe that triggers builds for
multiple boards.

TODO(crbug/1284439): Since this is in build repo, dedupe/move code to the
codesearch recipe module.
"""

PYTHON_VERSION_COMPATIBILITY = 'PY3'

DEPS = [
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
]


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


def download_clang_tool(api, clang_dir):
  """Download the translation_unit clang tool.

  Args:
    clang_dir: Directory containing clang scripts
  Return: The directory containing translation_unit
  """
  translation_unit_dir = api.path.mkdtemp()
  with api.context(cwd=clang_dir):
    api.step(
        name='download translation_unit clang tool',
        cmd=[
            'python3',
            clang_dir.join('scripts',
                           'update.py'), '--package=translation_unit',
            '--output-dir=' + str(translation_unit_dir)
        ])
  return translation_unit_dir


def run_clang_tool(api, clang_dir, chromiumos_build_dir, translation_unit_dir,
                   run_dir):
  """Run the translation_unit clang tool in a given run_dir.

  Args:
    clang_dir: Directory containing clang scripts
    chromiumos_build_dir: ChromiumOS build directory, e.g.
      chromiumos/src/out/amd64-generic/
    translation_unit_dir: Where translation_unit was downloaded
    run_dir: Where to run the translation_unit tool
  """
  try:
    with api.context(cwd=run_dir):
      api.step(
          name='run translation_unit clang tool in ' + str(run_dir),
          cmd=[
              clang_dir.join('scripts', 'run_tool.py'), '--tool',
              'translation_unit', '--tool-path',
              translation_unit_dir.join('bin'), '-p', chromiumos_build_dir,
              '--all'
          ])
  except api.step.StepFailure as f:  # pragma: no cover
    # For some files, the clang tool produces errors. This is a known issue,
    # but since it only affects very few files, we ignore these errors for now.
    # At least this means we can already have cross references support for the
    # files where it works.
    # TODO(crbug/1284439): Investigate translation_unit failures.
    api.step.active_result.presentation.step_text = f.reason_message()
    api.step.active_result.presentation.status = api.step.WARNING


def _create_kythe_index_pack(api,
                             index_pack_kythe_name,
                             chromiumos_dir,
                             build_dir,
                             compile_commands_json_file,
                             gn_targets_json_file,
                             output_dir,
                             corpus,
                             build_config=None):
  """Create the kythe index pack.

  Args:
    index_pack_kythe_name: Name of the Kythe index pack
    chromiumos_dir: Path to ChromiumOS
    build_dir: ChromiumOS build directory, e.g.
      chromiumos/src/out/amd64-generic/
    compile_commands_json_file: Path to compile_commands.json
    gn_targets_json_file: Path to gn_targets.json
    output_dir: The directory in which the KZIP will be output
    corpus: Corpus this KZIP belongs to
    build_config: Build configuration for this KZIP
  """
  # Prepare empty KZIP directory. This is needed since package_index requires a
  # Java kzip directory as input.
  # TODO(gavinmak): Make kzip dir input optional.
  java_kzips_dir = api.path.mkdtemp()

  exec_path = api.cipd.ensure_tool('infra/tools/package_index/${platform}',
                                   'latest')
  args = [
      '--checkout_dir',
      chromiumos_dir.join('src'), '--out_dir', build_dir, '--path_to_compdb',
      compile_commands_json_file, '--path_to_gn_targets', gn_targets_json_file,
      '--path_to_java_kzips', java_kzips_dir, '--path_to_archive_output',
      output_dir.join(index_pack_kythe_name), '--corpus', corpus
  ]
  if build_config:  # pragma: no cover
    args.extend(['--build_config', build_config])
  api.step('create kythe index pack', [exec_path] + args)


def _upload_kythe_index_pack(api, bucket_name, index_pack_kythe_path,
                             index_pack_kythe_name_with_timestamp):
  """Upload the kythe index pack to google storage.

  Args:
    bucket_name: Name of the google storage bucket to upload to
    index_pack_kythe_path: Path to the Kythe index pack
    index_pack_kythe_name_with_timestamp: Name of the Kythe index pack with
      timestamp
  """
  api.gsutil.upload(
      name='upload kythe index pack',
      source=index_pack_kythe_path,
      bucket=bucket_name,
      dest='prod/%s' % index_pack_kythe_name_with_timestamp)


def create_and_upload_kythe_index_pack(api,
                                       chromiumos_dir,
                                       bucket_name,
                                       timestamp,
                                       board,
                                       experimental,
                                       build_dir,
                                       compile_commands_json_file,
                                       gn_targets_json_file,
                                       output_dir,
                                       corpus,
                                       build_config=None):
  """Create the kythe index pack and upload it to google storage.

  Args:
    chromiumos_dir: Path to ChromiumOS
    bucket_name: Name of the google storage bucket to upload to
    timestamp: Timestamp at which we're creating the index pack, in integer
      seconds since the UNIX epoch
    board: Board used when building ChromiumOS
    experimental: Whether this KZIP is experimental
    build_dir: ChromiumOS build directory,
      e.g. chromiumos/src/out/amd64-generic/
    compile_commands_json_file: Path to compile_commands.json
    gn_targets_json_file: Path to gn_targets.json
    output_dir: The directory in which the KZIP will be output
    corpus: Corpus this KZIP belongs to
    build_config: Build configuration for this KZIP
  """
  index_pack_kythe_name = 'chromiumos_%s.kzip' % board
  experimental_suffix = '_experimental' if experimental else ''
  index_pack_kythe_name_with_timestamp = 'chromiumos_%s+%d%s.kzip' % (
      board, timestamp, experimental_suffix)
  _create_kythe_index_pack(api, index_pack_kythe_name, chromiumos_dir,
                           build_dir, compile_commands_json_file,
                           gn_targets_json_file, output_dir, corpus,
                           build_config)

  if api.tryserver.is_tryserver:  # pragma: no cover
    return

  _upload_kythe_index_pack(api, bucket_name,
                           output_dir.join(index_pack_kythe_name),
                           index_pack_kythe_name_with_timestamp)


def RunSteps(api):
  # TODO(crbug/1284439): Parametrize this when using initiator recipe.
  board = 'amd64-generic'
  experimental = False
  corpus = 'chromium.googlesource.com/chromiumos'

  # TODO(crbug/1284439): Increase coverage by using different packages.
  packages = [
      'chromeos-base/libbrillo',
      'chromeos-base/policy_utils',
      'chromeos-base/power_manager',
      'chromeos-base/chaps',
      'chromeos-base/cryptohome',
      'chromeos-base/metrics',
      'chromeos-base/oobe_config',
      'chromeos-base/session_manager-client',
      'chromeos-base/update_engine',
      'chromeos-base/libchrome',
  ]

  # Get infra/infra. Checking out infra automatically checks out depot_tools.
  checkout_dir = api.path['cache'].join('builder')
  with api.context(cwd=checkout_dir):
    api.bot_update.ensure_checkout(gclient_config=gclient_config(api))

  # Set up and build ChromiumOS.
  # TODO(crbug/1284439): Add sentinel file and handle cleaning up chroot.
  depot_tools_dir = checkout_dir.join('depot_tools')
  chromiumos_dir = checkout_dir.join('chromiumos')
  api.file.ensure_directory('ensure chromiumos dir', chromiumos_dir)
  with api.context(cwd=chromiumos_dir, env={'DEPOT_TOOLS_UPDATE': 0}):
    repo = depot_tools_dir.join('repo')
    api.step('repo init', [
        repo, 'init', '-u',
        'https://chromium.googlesource.com/chromiumos/manifest.git'
    ])
    api.step('repo sync', [repo, 'sync', '-j6'])

    cros_sdk = depot_tools_dir.join('cros_sdk')
    api.step('cros_sdk', [cros_sdk])
    api.step('export board', [cros_sdk, '--', 'export', 'BOARD=%s' % board])
    api.step('setup_board',
             [cros_sdk, '--', 'setup_board',
              '--board=%s' % board])

  # package_index_cros requires chromite/ in a parent directory.
  chromiumos_scripts_dir = chromiumos_dir.join('src', 'scripts')
  package_index_cros_dir = chromiumos_scripts_dir.join('package_index_cros')
  api.step('copy package_index_cros to chromiumos/src/scripts', [
      'cp', '-r',
      checkout_dir.join('infra', 'go', 'src', 'infra', 'cmd',
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

  # Download chromium clang tools.
  clang_dir = checkout_dir.join('clang')
  with api.context(cwd=checkout_dir):
    api.file.rmtree('remove previous instance of clang tools', clang_dir)
    api.git('clone',
            'https://chromium.googlesource.com/chromium/src/tools/clang')

  # Download and run the translation_unit tool in chromiumos/src dirs.
  translation_unit_dir = download_clang_tool(api, clang_dir)
  for d in [
      chromiumos_dir.join('src', 'platform2'),
      chromiumos_dir.join('src', 'aosp', 'external', 'libchrome'),
      chromiumos_dir.join('src', 'aosp', 'system', 'update_engine'),
  ]:
    run_clang_tool(
        api,
        clang_dir=clang_dir,
        chromiumos_build_dir=build_dir,
        translation_unit_dir=translation_unit_dir,
        run_dir=d)

  # Create the kythe index pack and upload it to google storage.
  output_kzip_dir = api.path['checkout'].join('output_kzip')
  api.file.ensure_directory('ensure output_kzip dir', output_kzip_dir)
  create_and_upload_kythe_index_pack(
      api=api,
      chromiumos_dir=chromiumos_dir,
      bucket_name='chrome-codesearch',
      timestamp=api.time.time(),
      board=board,
      experimental=experimental,
      build_dir=build_dir,
      compile_commands_json_file=build_dir.join('compile_commands.json'),
      gn_targets_json_file=build_dir.join('gn_targets.json'),
      output_dir=output_kzip_dir,
      corpus=corpus,
      build_config=None,
  )


def GenTests(api):
  yield api.test(
      'basic',
      api.step_data('repo init'),
      api.step_data('repo sync'),
  )
