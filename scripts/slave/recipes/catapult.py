# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'gitiles',
  'path',
  'properties',
  'python',
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
      # This is a commit after the latest fix to the script.
      branch='f849aad85ac3589c931197bff861faf0e2ef0ece')
  api.python.inline('Run SDK downloader', script_content, args=['--dest=.'])
  return api.path['slave_build'].join('google_appengine')


def GenSteps(api):
  buildername = api.properties.get('buildername')
  _CheckoutSteps(api, buildername)

  # The dashboard unit tests depend on Python modules in the App Engine SDK,
  # and the unit test runner script assumes that the SDK is in PYTHONPATH.
  sdk_path = _FetchAppEngineSDKSteps(api)
  modified_env = {
    'PYTHONPATH': api.path.pathsep.join(['%(PYTHONPATH)s', str(sdk_path)])
  }

  api.python('Util Tests',
             api.path['checkout'].join('base', 'util', 'run_tests.py'))
  api.python('Dashboard Tests',
             api.path['checkout'].join('dashboard', 'run_tests.py'),
             env=modified_env)


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
