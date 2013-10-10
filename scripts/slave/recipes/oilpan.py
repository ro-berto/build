# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
]

PERF_TESTS = [
  'dromaeo.domcoreattr',
]

def GenSteps(api):
  config_vals = {}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )
  api.chromium.set_config('chromium', **config_vals)
  api.gclient.set_config('oilpan', **config_vals)

  api.chromium.c.gyp_env.GYP_DEFINES['linux_strip_binary'] = 1
  api.chromium.c.gyp_env.GYP_DEFINES['target_arch'] = 'x64'

  yield (
    api.gclient.checkout(),
    api.chromium.runhooks(),
    api.chromium.compile(),
  )

  if api.chromium.c.HOST_PLATFORM == 'linux':
    build_exe = api.chromium.c.build_dir(api.chromium.c.build_config_fs,
                                         platform_ext={'win': '.exe'})

    test_dir = api.path.slave_build('test')
    api.gclient.apply_config('chrome_internal')
    api.gclient.spec_alias = 'test_checkout'
    api.gclient.c.solutions[0].revision = 'HEAD'
    api.gclient.c.got_revision_mapping.clear()
    yield api.path.makedirs('test_checkout', test_dir)
    yield api.gclient.checkout(cwd=test_dir)

    test_out_dir = test_dir('src', 'out', api.chromium.c.build_config_fs)
    yield api.path.makedirs('test_out_dir', test_out_dir)
    yield api.python.inline(
      'copy minidump_stackwalk',
      """
      import shutil
      import sys
      shutil.copy(sys.argv[1], sys.argv[2])
      """,
      args=[build_exe('minidump_stackwalk'), test_out_dir]
    )

    for test in PERF_TESTS:
      yield api.chromium.runtests(
        test_dir('src', 'tools', 'perf', 'run_benchmark'),
        ['-v', '--output-format=buildbot', '--browser=exact',
         '--browser-executable', build_exe('chrome'), test],
        name=test, results_url='https://chromeperf.appspot.com',
        annotate='graphing', perf_dashboard_id='linux-release',
        python_mode=True
      )

def GenTests(api):
  for plat in ('linux', 'win', 'mac'):
    yield (
      api.test('basic_%s' % plat) +
      api.properties(TARGET_BITS=64) +
      api.platform(plat, 64)
    )
