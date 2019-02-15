# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/cipd',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/python',
  'recipe_engine/time',
  'zip',
]

from recipe_engine.recipe_api import Property

CELAB_REPO = "https://chromium.googlesource.com/enterprise/cel"

CI_POOL_NAME = "celab-ci"
CI_POOL_SIZE = 5

TRY_POOL_NAME = "celab-try"
TRY_POOL_SIZE = 5


def _get_bin_directory(api, checkout):
  bin_dir = checkout.join('out')
  if api.platform.is_linux:
    bin_dir = bin_dir.join('linux_amd64', 'bin')
  elif api.platform.is_win:
    bin_dir = bin_dir.join('windows_amd64', 'bin')
  return bin_dir


def _get_ctl_binary_name(api):
  suffix = '.exe' if api.platform.is_win else ''
  return "cel_ctl" + suffix


def RunSteps(api):
  # Checkout the CELab repo
  go_root = api.path['start_dir'].join('go')
  src_root = go_root.join('src', "chromium.googlesource.com", "enterprise")
  api.file.ensure_directory('init src_root if not exists', src_root)

  with api.context(cwd=src_root):
    api.gclient.set_config('celab')
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()
  checkout = api.path['checkout']

  # Install Go & Protoc
  packages = {}
  packages['infra/go/${platform}'] = 'version:1.11.2'
  packages['infra/tools/protoc/${platform}'] = 'protobuf_version:v3.6.1'
  packages['infra/third_party/cacert'] = 'date:2017-01-18'
  packages_root = api.path['start_dir'].join('packages')
  api.cipd.ensure(packages_root, packages)

  add_paths = [
    go_root.join('bin'),
    packages_root,
    packages_root.join('bin'),
  ]

  # Build CELab
  cert_file = packages_root.join('cacert.pem')
  goenv = {"GOPATH": go_root, "GIT_SSL_CAINFO": cert_file}
  with api.context(cwd=checkout, env=goenv, env_suffixes={'PATH': add_paths}):
    api.python('install deps', 'build.py', ['deps', '--install', '--verbose'])
    api.python('build', 'build.py', ['build', '--verbose'])

  # Upload binaries (cel_ctl and resources/*) for CI builds
  bucket = api.buildbucket.build.builder.bucket
  if bucket == 'ci':
    output_dir = _get_bin_directory(api, checkout)
    cel_ctl = _get_ctl_binary_name(api)
    zip_out = api.path['start_dir'].join('cel.zip')
    pkg = api.zip.make_package(output_dir, zip_out)
    pkg.add_file(output_dir.join(cel_ctl))
    pkg.add_directory(output_dir.join('resources'))
    pkg.zip('zip archive')

    today = api.time.utcnow().date()
    gs_dest = '%s/%s/%s/cel.zip' % (
      api.buildbucket.builder_name,
      today.strftime('%Y/%m/%d'),
      api.buildbucket.build.id)
    api.gsutil.upload(
      source=zip_out,
      bucket='celab',
      dest=gs_dest,
      name='upload CELab binaries',
      link_name='CELab binaries')

  # Run tests for specific Linux CI/Try builds.
  if api.platform.is_linux:
    if bucket == 'ci':
      _RunTests(api, checkout, CI_POOL_NAME, CI_POOL_SIZE)
    elif bucket == 'try' and api.buildbucket.builder_name == "tests":
      _RunTests(api, checkout, TRY_POOL_NAME, TRY_POOL_SIZE)


def _RunTests(api, checkout, pool_name, pool_size):
  host_dir = api.path['start_dir'].join('hosts')
  error_logs_dir = api.path['start_dir'].join('logs')
  api.file.ensure_directory('init host_dir if not exists', host_dir)
  api.file.ensure_directory('init error_logs_dir if not exists', error_logs_dir)

  # Get a unique storage prefix for these tests (diff runs share the bucket)
  storage_prefix = 'test-run-%s' % api.buildbucket.build.id

  # Generate the host files that we'll use in ./run_tests.py.
  with api.context(cwd=checkout.join('scripts', 'tests')):
    api.python('generate host files',
      'generate_host_files.py',
      [
        '--template', '../../examples/schema/host/example.host.textpb',
        '--projects', ';'.join(["%s-%03d" % (pool_name, i) for i in xrange(
            1, pool_size + 1)]),
        '--storage_bucket', '%s-assets' % pool_name,
        '--storage_prefix', storage_prefix,
        '--destination_dir', host_dir
      ],
      venv=True)

  # Run our tests and catch test failures.
  with api.context(cwd=checkout):
    try:
      api.python('run all tests',
        'run_tests.py',
        [
          '--hosts', host_dir,
          '--shared_provider_storage', '%s-assets' % pool_name,
          '--error_logs_dir', error_logs_dir,
          '--noprogress', '-vv'
        ],
        venv=True)
    except:
      # Save the error logs in our logs bucket.
      zip_out = api.path['start_dir'].join('logs.zip')
      pkg = api.zip.make_package(error_logs_dir, zip_out)
      pkg.add_directory(error_logs_dir)
      pkg.zip('zip logs archive')

      today = api.time.utcnow().date()
      gs_dest = '%s/%s/%s/logs.zip' % (
        api.buildbucket.builder_name,
        today.strftime('%Y/%m/%d'),
        api.buildbucket.build.id)
      api.gsutil.upload(
        source=zip_out,
        bucket='%s-logs' % pool_name,
        dest=gs_dest,
        name='upload CELab test logs',
        link_name='Test logs')

      raise
    finally:
      # TODO: Clean up storage prefix when the test run ends.
      #       It's already automatically deleted after 1 day.
      pass


def GenTests(api):
  yield (
      api.test('basic_try') +
      api.buildbucket.try_build(project='celab', bucket='try',
                                git_repo=CELAB_REPO)
  )
  yield (
      api.test('tests_try') +
      api.buildbucket.try_build(project='celab', bucket='try',
                                builder='tests',
                                git_repo=CELAB_REPO)
  )
  yield (
      api.test('basic_ci_linux') +
      api.platform('linux', 64) +
      api.buildbucket.ci_build(project='celab', bucket='ci',
                               git_repo=CELAB_REPO)
  )
  yield (
      api.test('basic_ci_windows') +
      api.platform('win', 64) +
      api.buildbucket.ci_build(project='celab', bucket='ci',
                               git_repo=CELAB_REPO)
  )
  yield (
      api.test('failed_tests_ci_linux') +
      api.platform('linux', 64) +
      api.buildbucket.ci_build(project='celab', bucket='ci',
                               git_repo=CELAB_REPO) +
      api.step_data('run all tests', retcode=1)
  )
