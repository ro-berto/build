# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'gitiles',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
]


def _CheckoutSteps(api, buildername):
  """Checks out the catapult repo (and any dependencies) using gclient."""
  api.gclient.set_config('catapult')
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()


def _FetchAppEngineSDKSteps(api):
  """Fetches the App Engine SDK and returns its path.

  This uses a downloader script in the infra repo to download a script
  which is then used to download and unpack the SDK itself.
  """
  script_content = api.gitiles.download_file(
      'https://chromium.googlesource.com/infra/infra',
      'bootstrap/get_appengine.py',
      step_name='Fetch SDK downloader',
      # This is a commit after the latest fix to the script,
      # which includes retrying requests.
      branch='fd119c547fd4e56eeab77d138b0426022ae1d159')
  api.python.inline('Run SDK downloader', script_content, args=['--dest=.'])
  return api.path['slave_build'].join('google_appengine')


def RunSteps(api):
  buildername = api.properties.get('buildername')
  _CheckoutSteps(api, buildername)

  # The dashboard unit tests depend on Python modules in the App Engine SDK,
  # and the unit test runner script assumes that the SDK is in PYTHONPATH.
  sdk_path = _FetchAppEngineSDKSteps(api)
  modified_env = {
    'PYTHONPATH': api.path.pathsep.join(['%(PYTHONPATH)s', str(sdk_path)])
  }

  # The sandbox is needed to run chrome on linux, but is harmless to set on
  # other platforms.
  sandbox_env = {
    'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'
  }

  api.python('Build Python Tests',
             api.path['checkout'].join('catapult_build', 'bin', 'run_py_tests'))
  api.python('Catapult Base Tests',
             api.path['checkout'].join('catapult_base', 'bin', 'run_tests'))
  api.python('Dependency Manager Tests',
             api.path['checkout'].join(
                 'dependency_manager', 'bin', 'run_tests'))
  api.python('Dashboard Dev Server Tests Stable',
              api.path['checkout'].join(
                  'dashboard', 'bin', 'run_dev_server_tests'),
              ['--no-install-hooks', '--no-use-local-chrome',
               '--channel=stable'])
  api.python('Dashboard Dev Server Tests Canary',
              api.path['checkout'].join(
                  'dashboard', 'bin', 'run_dev_server_tests'),
              ['--no-install-hooks', '--no-use-local-chrome',
               '--channel=canary'])
  api.python('Dashboard Python Tests',
             api.path['checkout'].join('dashboard', 'bin', 'run_py_tests'),
             ['--no-install-hooks'],
             env=modified_env)
  api.python('Tracing Python Tests',
             api.path['checkout'].join('tracing', 'bin', 'run_py_tests'),
             ['--no-install-hooks'])
  api.python('Tracing Dev Server Tests Stable',
             api.path['checkout'].join(
                 'tracing', 'bin', 'run_dev_server_tests'),
             ['--no-install-hooks',
              '--no-use-local-chrome',
              '--channel=stable'])
  api.python('Py-vulcanize Tests',
             api.path['checkout'].join(
                 'third_party', 'py_vulcanize', 'bin', 'run_py_tests'),
             ['--no-install-hooks'])
  api.python('Perf Insights Dev Server Tests Stable',
             api.path['checkout'].join(
                 'perf_insights', 'bin', 'run_dev_server_tests'),
             ['--no-install-hooks',
              '--no-use-local-chrome',
              '--channel=stable'])
  api.python('Perf Insights Dev Server Tests Canary',
             api.path['checkout'].join(
                 'perf_insights', 'bin', 'run_dev_server_tests'),
             ['--no-install-hooks',
              '--no-use-local-chrome',
              '--channel=canary'])
  api.python('Systrace Tests',
             api.path['checkout'].join('systrace', 'bin', 'run_tests'))
  api.python('Telemetry Tests with Stable Browser',
             api.path['checkout'].join('telemetry', 'bin', 'run_tests'),
             ['--browser=reference',
              '--start-xvfb'],
              env=sandbox_env)
  if not api.platform.is_win:
    # D8/vinn currently unavailable on Windows.
    # TODO(sullivan): Add these tests on Windows when available.
    api.python('Vinn Tests',
               api.path['checkout'].join('third_party', 'vinn', 'run_test'))
    api.python('Tracing D8 Tests',
               api.path['checkout'].join('tracing', 'bin', 'run_vinn_tests'))
    api.python('Perf Vinn Insights Tests',
               api.path['checkout'].join(
                   'perf_insights', 'bin', 'run_vinn_tests'))
    # TODO(nduca): re-enable these if they should be working on Windows.
    api.python('Perf Insights Python Tests',
               api.path['checkout'].join(
                   'perf_insights', 'bin', 'run_py_tests'),
               ['--no-install-hooks'])
    # Test failing on Windows:
    # https://github.com/catapult-project/catapult/issues/1816
    api.python('Tracing Dev Server Tests Canary',
               api.path['checkout'].join(
                   'tracing', 'bin', 'run_dev_server_tests'),
               ['--no-install-hooks',
                '--no-use-local-chrome',
                '--channel=canary'])
  if api.platform.is_linux:
    api.python('Devil Python Tests',
               api.path['checkout'].join('devil', 'bin', 'run_py_tests'))


def GenTests(api):
  yield (
    api.test('basic') +
    api.properties(mastername='master.client.catapult',
                   buildername='windows',
                   slavename='windows_slave') +
    api.step_data('Fetch SDK downloader',
                  api.gitiles.make_encoded_file(
                      '"<simulated contents of get_appengine.py>"'))
  )
