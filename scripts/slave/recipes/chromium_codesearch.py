# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze

DEPS = [
  'bot_update',
  'chromium',
  'commit_position',
  'gclient',
  'gsutil',
  'json',
  'path',
  'properties',
  'python',
  'raw_io',
  'step',
]

BUCKET_NAME = 'chrome-codesearch'
CHROMIUM_GIT_URL = 'https://chromium.googlesource.com'

# Lists the additional repositories that should be checked out to be included
# in the source archive that is indexed by Codesearch.
ADDITIONAL_REPOS = freeze({
  'infra': '%s/infra/infra' % CHROMIUM_GIT_URL,
  'tools/chrome-devtools-frontend':\
      '%s/chromium/tools/chrome-devtools-frontend' % CHROMIUM_GIT_URL,
  'tools/chromium-jobqueue':\
      '%s/chromium/tools/chromium-jobqueue' % CHROMIUM_GIT_URL,
  'tools/chromium-shortener':\
      '%s/chromium/tools/chromium-shortener' % CHROMIUM_GIT_URL,
  'tools/command_wrapper/bin':\
      '%s/chromium/tools/command_wrapper/bin' % CHROMIUM_GIT_URL,
  'tools/commit-queue': '%s/chromium/tools/commit-queue' % CHROMIUM_GIT_URL,
  'tools/depot_tools': '%s/chromium/tools/depot_tools' % CHROMIUM_GIT_URL,
  'tools/deps2git': '%s/chromium/tools/deps2git' % CHROMIUM_GIT_URL,
  'tools/gsd_generate_index':\
      '%s/chromium/tools/gsd_generate_index' % CHROMIUM_GIT_URL,
  'tools/perf': '%s/chromium/tools/perf' % CHROMIUM_GIT_URL,
})

SPEC = freeze({
  # The builders have the following parameters:
  # - chromium_config_kwargs: parameters for the config of the chromium module.
  # - chromium_runhooks_kwargs: parameters for the runhooks step.
  # - compile_targets: the compile targets.
  # - create_index_pack: Whether to create an index pack separate from source.
  # - environment: The environment of the bot (prod / staging).
  # - package_filename: The prefix of the name of the source archive.
  # - platform: The platform for which the code is compiled.
  'builders': {
    'Chromium Linux Codesearch': {
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
      },
      'compile_targets': [
        'all',
      ],
      'create_index_pack': False,
      'environment': 'prod',
      'package_filename': 'chromium-src',
      'platform': 'linux',
    },
    'ChromiumOS Codesearch': {
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'chromeos',
      },
      'compile_targets': [
        'all',
      ],
      'create_index_pack': False,
      'environment': 'prod',
      'package_filename': 'chromiumos-src',
      'platform': 'chromeos',
    },
    'Chromium Linux Codesearch Staging': {
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
      },
      'compile_targets': [
        'all',
      ],
      'create_index_pack': True,
      'environment': 'staging',
      'package_filename': 'chromium-src',
      'platform': 'linux',
    },
    'ChromiumOS Codesearch Staging': {
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'chromeos',
      },
      'compile_targets': [
        'all',
      ],
      'create_index_pack': True,
      'environment': 'staging',
      'package_filename': 'chromiumos-src',
      'platform': 'chromeos',
    },
  },
})


def GenSteps(api):
  buildername = api.properties.get('buildername')

  bot_config = SPEC.get('builders', {}).get(buildername)

  # Checkout the repositories that are either directly needed or should be
  # included in the source archive.
  gclient_config = api.gclient.make_config('chromium')
  solution = gclient_config.solutions.add()
  solution.name = 'clang_indexer'
  solution.url = \
      'https://chrome-internal.googlesource.com/chrome/tools/clang_indexer'
  for name, url in ADDITIONAL_REPOS.iteritems():
    solution = gclient_config.solutions.add()
    solution.name = name
    solution.url = url
  api.gclient.c = gclient_config
  update_step = api.bot_update.ensure_checkout()
  api.chromium.set_build_properties(update_step.json.output['properties'])

  # Compile the code using clang.
  api.chromium.set_config('codesearch',
                          **bot_config.get('chromium_config_kwargs', {}))
  api.chromium.runhooks()
  targets = bot_config.get('compile_targets', [])
  debug_path = api.path['checkout'].join('out', api.chromium.c.BUILD_CONFIG)
  command = ['ninja', '-C', debug_path] + list(targets)
  # Add the parameters for creating the compilation database.
  command += ['-t', 'compdb', 'cc', 'cxx', 'objc', 'objcxx']
  result = api.step('generate compilation database', command,
                    stdout=api.raw_io.output())

  api.chromium.compile(targets, force_clobber=True)

  # Copy the created output to the correct directory. When running the clang
  # tool, it is assumed by the scripts that the compilation database is in the
  # out/Debug directory, and named 'compile_commands.json'.
  api.step('copy compilation database',
           ['cp', api.raw_io.input(data=result.stdout),
            debug_path.join('compile_commands.json')])

  # Now compile the code for real.
  if bot_config.get('create_index_pack'):
    # Compile the clang tool
    script_path = api.path.sep.join(['tools', 'clang', 'scripts', 'update.sh'])
    api.step('compile translation_unit clang tool',
             [script_path, '--force-local-build', '--without-android',
              '--with-chrome-tools', 'translation_unit'],
             cwd=api.path['checkout'])

    # Run the clang tool
    args = [api.path['checkout'].join('third_party', 'llvm-build',
                                      'Release+Asserts', 'bin',
                                      'translation_unit'),
            debug_path, '--all']
    try:
      api.python(
          'run translation_unit clang tool',
          api.path['checkout'].join('tools', 'clang', 'scripts', 'run_tool.py'),
          args)
    except api.step.StepFailure as f:
      # For some files, the clang tool produces errors. This is a known issue,
      # but since it only affects very few files (currently 9), we ignore these
      # errors for now. At least this means we can already have cross references
      # support for the files where it works.
      api.step.active_result.presentation.step_text = f.reason_message()

    # Create the index pack
    got_revision_cp = api.chromium.build_properties.get('got_revision_cp')
    commit_position = api.commit_position.parse_revision(got_revision_cp)
    platform = bot_config.get('platform', 'linux')
    index_pack_name = 'index_pack_%s_%s.zip' % (platform, commit_position)
    api.python('create index pack',
               api.path['build'].join('scripts', 'slave', 'chromium',
                                      'package_index.py'),
               ['--path-to-compdb', debug_path.join('compile_commands.json'),
                '--path-to-archive-output', debug_path.join(index_pack_name)])

    # Upload the index pack
    environment = bot_config.get('environment', 'prod')
    api.gsutil.upload(
        name='upload index pack',
        source=debug_path.join(index_pack_name),
        bucket=BUCKET_NAME,
        dest='%s/%s' % (environment, index_pack_name)
    )

    # Package the source code.
    tarball_name = 'chromium_src_%s_%s.tar.bz2' % (platform, commit_position)
    api.python('archive source',
               api.path['build'].join('scripts','slave',
                                      'archive_source_codesearch.py'),
               ['src', 'build', 'infra', 'tools', '/usr/include', '-f',
                tarball_name])

    # Upload the source code.
    api.gsutil.upload(
        name='upload source tarball',
        source=api.path['slave_build'].join(tarball_name),
        bucket=BUCKET_NAME,
        dest='%s/%s' % (environment, tarball_name)
    )
  else:
    # Run the package_source.py script that creates and uploads the source
    # archive which also includes the .index files generated by the
    # clang_indexer. The script inspects factory properties, so the options are
    # provided in this format.
    fake_factory_properties = {
        'package_filename': bot_config.get('package_filename', ''),
    }
    args = [
        '--build-properties', api.json.dumps(api.chromium.build_properties),
        '--factory-properties', api.json.dumps(fake_factory_properties),
        '--path-to-compdb', api.raw_io.input(data=result.stdout),
        '--environment', bot_config.get('environment', ''),
    ]
    api.python('package_source',
               api.path['build'].join('scripts', 'slave', 'chromium',
                                      'package_source.py'),
               args)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for buildername, _ in SPEC['builders'].iteritems():
    test = (
      api.test('full_%s' % (_sanitize_nonalpha(buildername))) +
      api.step_data('generate compilation database',
                    stdout=api.raw_io.output('some compilation data')) +
      api.properties.generic(buildername=buildername, mastername='chromium.fyi')
    )

    yield test

  yield (
    api.test(
        'full_%s_fail' % _sanitize_nonalpha('ChromiumOS Codesearch Staging')) +
    api.step_data('generate compilation database',
                  stdout=api.raw_io.output('some compilation data')) +
    api.step_data('run translation_unit clang tool', retcode=2) +
    api.properties.generic(buildername='ChromiumOS Codesearch Staging',
                           mastername='chromium.fyi')
  )
