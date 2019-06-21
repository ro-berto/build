# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_checkout',
  'chromium_tests',
  'depot_tools/bot_update',
  'depot_tools/cipd',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'recipe_engine/time',
  'zip',
]

from recipe_engine.recipe_api import Property

CELAB_REPO = "https://chromium.googlesource.com/enterprise/cel"
CHROMIUM_REPO = "https://chromium.googlesource.com/chromium/src"


def _get_bin_directory(api, bin_root):
  bin_dir = bin_root
  if api.platform.is_linux:
    bin_dir = bin_dir.join('linux_amd64', 'bin')
  elif api.platform.is_win:
    bin_dir = bin_dir.join('windows_amd64', 'bin')
  return bin_dir


def _get_ctl_binary_name(api):
  suffix = '.exe' if api.platform.is_win else ''
  return "cel_ctl" + suffix


def _get_python_packages(api, checkout):
  """Returns the full path of the python whl package files."""
  out_dir = checkout.join('out')
  return api.file.glob_paths('find python packages', out_dir, '*.whl',
    test_data=['test.whl'])


def RunSteps(api):
  project = api.buildbucket.build.builder.project

  if project == 'celab':
    _RunStepsCelab(api)
  elif project == 'chromium':
    _RunStepsChromium(api)
  else:
    raise ValueError('Invalid `project`. Accepted values: celab, chromium.')


def _RunStepsCelab(api):
  checkout = _CheckoutCelabRepo(api)

  # Build CELab binaries from source.
  bin_dir = _BuildCelabFromSource(api, checkout)

  # Upload binaries (cel_ctl and resources/*, plus the python package of the
  # test framework) for CI builds
  bucket = api.buildbucket.build.builder.bucket
  if bucket == 'ci':
    _UploadCelabBinariesToStorage(api, checkout, bin_dir)

  # Run tests for CI/Try builders that specify it.
  tests = api.properties.get('tests')
  if tests:
    _RunTests(
      api,
      checkout.join('test'),
      checkout.join('scripts').join('tests'),
      '../../examples/schema/host/example.host.textpb',
      tests)


def _RunStepsChromium(api):
  version = api.properties.get('celab_version')
  tests = api.properties.get('tests')
  if not version or not tests:
    raise ValueError('Chromium bots must define `celab_version` and `tests`.')

  # Build Chromium binaries from source and get CELab from CIPD.
  checkout = _CheckoutChromiumRepo(api)
  test_root = checkout.join('chrome', 'browser', 'policy', 'e2e_test')
  chromium_bin_dir = _BuildChromiumFromSource(api, test_root)
  celab_bin_dir = _GetCelabFromCipd(api, version)

  # Run tests for all chromium bots.
  cel_ctl = celab_bin_dir.join(_get_ctl_binary_name(api))
  installer = chromium_bin_dir.join("mini_installer.exe")
  chromedriver = chromium_bin_dir.join("chromedriver.exe")
  test_py_args = '--cel_ctl=%s' % cel_ctl
  test_py_args += ' --test_arg=--chrome_installer=%s' % installer
  test_py_args += ' --test_arg=--chromedriver=%s' % chromedriver
  _RunTests(
    api,
    test_root,
    test_root.join('infra'),
    'template.host.textpb',
    tests,
    test_py_args)


def _GetCelabFromCipd(api, version):
  packages_root = api.path['start_dir'].join('packages')
  api.cipd.ensure(packages_root, {'infra/celab/celab/${platform}': version})
  return _get_bin_directory(api, packages_root)


def _CheckoutCelabRepo(api):
  # Checkout the CELab repo
  go_root = api.path['start_dir'].join('go')
  src_root = go_root.join('src', "chromium.googlesource.com", "enterprise")
  api.file.ensure_directory('init src_root if not exists', src_root)

  with api.context(cwd=src_root):
    api.gclient.set_config('celab')
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()
  return api.path['checkout']


def _BuildCelabFromSource(api, checkout):
  go_root = api.path['start_dir'].join('go')

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
    api.python(
      'create python package',
      'build.py', ['create_package', '--verbose'],
      venv=True)

  return _get_bin_directory(api, checkout.join('out'))


def _CheckoutChromiumRepo(api):
  with api.chromium.chromium_layout():
    bot_config = {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'chromium_apply_config': ['mb'],
        'chromium_config_kwargs': {
            'BUILD_CONFIG': 'Release',
            'TARGET_BITS': 64,
        },
    }
    api.chromium_tests.configure_build(bot_config)
    api.chromium_checkout.ensure_checkout(bot_config)
    api.chromium.runhooks()

  return api.path['checkout']


def _BuildChromiumFromSource(api, test_root):
  with api.chromium.chromium_layout():
    compile_targets = ['chrome/installer/mini_installer', 'chromedriver']
    api.chromium_tests.run_mb_and_compile(
      compile_targets,
      isolated_targets=[],
      mb_config_path=test_root.join('infra', 'config.pyl'),
      name_suffix=' (with patch)')

  return api.chromium.output_dir


def _UploadCelabBinariesToStorage(api, checkout, bin_dir):
  cel_ctl = _get_ctl_binary_name(api)
  zip_out = api.path['start_dir'].join('cel.zip')
  pkg = api.zip.make_package(checkout.join('out'), zip_out)
  pkg.add_file(bin_dir.join(cel_ctl))
  pkg.add_directory(bin_dir.join('resources'))
  for package_file in _get_python_packages(api, checkout):
    pkg.add_file(package_file)
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


def _RunTests(api, test_root, test_scripts_root, host_file_template, tests,
              test_py_args = ""):
  pool_name = api.properties.get('pool_name')
  pool_size = api.properties.get('pool_size')

  if not pool_name or not pool_size:
    raise ValueError('pool_name and pool_size must be defined with `tests`.')

  host_dir = api.path['start_dir'].join('hosts')
  logs_dir = api.path['start_dir'].join('logs')
  with api.step.nest('setup tests'):
    api.file.ensure_directory('init host_dir if not exists', host_dir)
    api.file.ensure_directory('init logs_dir if not exists', logs_dir)

    # Install required package for gsutil.
    packages_root = api.path['start_dir'].join('packages_tests')
    packages = {'infra/gcloud/${platform}': 'version:251.0.0.chromium0'}
    api.cipd.ensure(packages_root, packages)
    add_paths = [packages_root.join('bin')]

    # Get a unique storage prefix for these tests (diff runs share the bucket)
    storage_prefix = 'test-run-%s' % api.buildbucket.build.id

    # Generate the host files that we'll use in ./run_tests.py.
    with api.context(cwd=test_scripts_root):
      api.python('generate host files',
        'generate_host_files.py',
        [
          '--template', host_file_template,
          '--projects', ';'.join(["%s-%03d" % (pool_name, i) for i in xrange(
              1, pool_size + 1)]),
          '--storage_bucket', '%s-assets' % pool_name,
          '--storage_prefix', storage_prefix,
          '--destination_dir', host_dir
        ],
        venv=True)

  # Run our tests and catch test failures.
  with api.context(cwd=test_root, env_suffixes={'PATH': add_paths}):
    extra_args = []
    if test_py_args:
      extra_args += ['--test_py_args=%s' % test_py_args]

    try:
      api.python('run all tests',
        'run_tests.py',
        [
          '--tests', tests,
          '--hosts', host_dir,
          '--test_py', 'test.py',
          '--shared_provider_storage', '%s-assets' % pool_name,
          '--error_logs_dir', logs_dir,
          '--noprogress', '-v', '1'
        ] + extra_args,
        venv=True)
    except:
      storage_logs = '%s-logs' % pool_name

      try:
        # Parse the test summary file and organize results in a readable way.
        _ParseTestSummary(api, storage_logs, logs_dir)
      except:
        raise
      finally:
        # We upload *all* logs here (including those already uploaded).
        # It's better to upload (small) logs twice than to not upload them at
        # all. They are automatically deleted after 30 days (bucket policy).
        _ZipAndUploadDirectory(
          api,
          storage_logs,
          logs_dir,
          'all_logs.zip',
          'CELab Test Logs')

      raise
    finally:
      # TODO: Clean up storage prefix when the test run ends.
      #       It's already automatically deleted after 1 day.
      pass


# Zips the content of a directory and uploads the zip file to a given bucket.
def _ZipAndUploadDirectory(api, bucket, directory, zip_filename, display_name):
  zip_out = api.path['start_dir'].join(zip_filename)
  pkg = api.zip.make_package(directory, zip_out)
  pkg.add_directory(directory)
  pkg.zip('zip logs archive')

  today = api.time.utcnow().date()
  gs_dest = '%s/%s/%s/%s' % (
    api.buildbucket.builder_name,
    today.strftime('%Y/%m/%d'),
    api.buildbucket.build.id,
    zip_filename)
  return api.gsutil.upload(
    source=zip_out,
    bucket=bucket,
    dest=gs_dest,
    name='upload %s' % display_name,
    link_name=display_name)


# Parses the summary.json file created by run_tests.py, organizes the steps
# presentation of tests and creates separate zips for each test logs.
def _ParseTestSummary(api, storage_logs, logs_dir):
  summary_path = logs_dir.join("summary.json")

  with api.step.nest('test summary') as summary_step:
    summary_presentation = summary_step.presentation
    tests_summary = api.json.read('parse summary', summary_path).json.output

    for test in tests_summary:
      try:
        with api.step.nest(test) as test_step:
          test_presentation = test_step.presentation
          result = tests_summary[test]

          test_presentation.status = api.step.SUCCESS

          if not result['success']:
            test_presentation.status = api.step.FAILURE
            summary_presentation.status = api.step.FAILURE

          if 'output' in result:
            logs = api.file.read_text('read logs', result['output'])
            test_presentation.logs["test.py output"] = logs.splitlines()

          # Upload logs if they exist (when test fails after Deployment starts)
          compute_logs_dir = logs_dir.join(test)
          if api.path.exists(compute_logs_dir):
            upload_step = _ZipAndUploadDirectory(
              api,
              storage_logs,
              compute_logs_dir,
              test + '.zip',
              'Compute logs')

            # Merge the gsutil links in the Test step.
            upload_presentation = upload_step.presentation
            for link in upload_presentation.links:
              test_presentation.links[link] = upload_presentation.links[link]
      except Exception as e:
        summary_presentation.logs["exception %s" % test] = repr(e).splitlines()


def GenTests(api):
  yield (
      api.test('basic_try') +
      api.buildbucket.try_build(project='celab', bucket='try',
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
      api.properties(tests='*', pool_name='celab-ci', pool_size=5) +
      api.buildbucket.ci_build(project='celab', bucket='ci',
                               git_repo=CELAB_REPO) +
      api.step_data('run all tests', retcode=1) +
      api.step_data('test summary.parse summary',
                    api.json.output({
                      '1st test': {'success': False, 'output': '/some/file'},
                      '2nd test': {'success': True, 'output': '/other/file'},
                      '3rd test': {'success': True, 'output': '/missing'}})) +
      api.step_data('test summary.1st test.read logs',
            api.file.read_text('first\ntest\nlogs')) +
      api.step_data('test summary.2nd test.read logs',
            api.file.read_text('second\ntest\nlogs')) +
      api.step_data('test summary.3rd test.read logs',
            api.file.errno('EEXIST')) +
      api.path.exists(api.path['start_dir'].join('logs', '1st test'))
  )
  yield (
      api.test('failed_tests_no_summary_ci_linux') +
      api.platform('linux', 64) +
      api.properties(tests='*', pool_name='celab-ci', pool_size=5) +
      api.buildbucket.ci_build(project='celab', bucket='ci',
                               git_repo=CELAB_REPO) +
      api.step_data('run all tests', retcode=1) +
      api.step_data('test summary.parse summary', retcode=1)
  )
  yield (
      api.test('windows_quick_tests') +
      api.properties(tests='sample.test', pool_name='celab-try', pool_size=5) +
      api.platform('win', 64) +
      api.buildbucket.ci_build(project='celab', bucket='try',
                               builder='windows-quick-tests',
                               git_repo=CELAB_REPO)
  )
  yield (
      api.test('misconfigured_tests') +
      api.properties(tests='sample.test') +
      api.platform('win', 64) +
      api.buildbucket.ci_build(project='celab', bucket='try',
                               builder='misconfigured-quick-tests',
                               git_repo=CELAB_REPO) +
      api.expect_exception('ValueError')
  )
  yield (
      api.test('chromium_try') +
      api.properties(tests='chromium.test', celab_version='version:1.0.0',
                     pool_name='chromium-try', pool_size=5,
                     mastername='tryserver.chromium.win', bot_id='test_bot') +
      api.platform('win', 64) +
      api.buildbucket.try_build(project='chromium',
                                bucket='luci.chromium.try',
                                builder='win-celab-try-rel',
                                git_repo=CHROMIUM_REPO)
  )
  yield (
      api.test('chromium_no_version') +
      api.properties(tests='chromium.test',
                     mastername='tryserver.chromium.win', bot_id='test_bot') +
      api.platform('win', 64) +
      api.buildbucket.try_build(project='chromium',
                                bucket='luci.chromium.try',
                                builder='win-celab-try-rel',
                                git_repo=CHROMIUM_REPO) +
      api.expect_exception('ValueError')
  )
  yield (
      api.test('invalid_project') +
      api.buildbucket.ci_build(project='other-project') +
      api.expect_exception('ValueError')
  )
