# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This recipe is intended to control all of the GPU related bots:
#   chromium.gpu
#   chromium.gpu.fyi
#   The GPU bots on the chromium.webkit waterfall
#   The GPU bots on the tryserver.chromium waterfall

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'rietveld',
  'step_history',
]

SIMPLE_TESTS_TO_RUN = [
  'content_gl_tests',
  'gles2_conform_test',
  'gl_tests'
]

def GenSteps(api):
  # These values may be replaced by external configuration later
  dashboard_upload_url = 'https://chromeperf.appspot.com'
  generated_dir = api.path.slave_build('content_gpu_data', 'generated')
  reference_dir = api.path.slave_build('content_gpu_data', 'reference')
  gsutil = api.path.build('scripts', 'slave', 'gsutil',
                          platform_ext={'win': '.bat'})

  is_release_build = api.properties.get('build_config', 'Release') == 'Release'
  # The infrastructure team has recommended not to use git yet on the
  # bots, but it's useful -- even necessary -- when testing locally.
  # To use, pass "use_git=True" as an argument to run_recipe.py.
  use_git = api.properties.get('use_git', False)

  # Currently content_browsertests' pixel tests use the build revision
  # (which is assumed to be the SVN revision of src/) to know whether
  # to regenerate the reference images. This mechanism should be
  # changed, but for now, pass down the intended value. Note that this
  # is overridden below using the correct values from gclient. This is
  # here in order to still support commenting out the block of code
  # below while testing locally.
  build_revision = api.properties['revision']

  api.chromium.set_config('chromium', GIT_MODE=use_git)
  # This is needed to make GOMA work properly on Mac.
  if api.platform.is_mac:
    api.chromium.set_config('chromium_clang', GIT_MODE=use_git)
  api.gclient.apply_config('chrome_internal')

  # Don't skip the frame_rate data, as it's needed for the frame rate tests.
  # Per iannucci@, it can be relied upon that solutions[1] is src-internal.
  # Consider adding a 'gpu' module so that this can be managed in a
  # 'gpu' config.
  del api.gclient.c.solutions[1].custom_deps[
    'src/chrome/test/data/perf/frame_rate/private']

  api.chromium.c.gyp_env.GYP_DEFINES['internal_gles2_conform_tests'] = 1

  # If you want to stub out the checkout/runhooks/compile steps,
  # uncomment this line and then comment out the associated block of
  # yield statements below.
  # api.path.set_dynamic_path('checkout', api.path.slave_build('src'))

  yield api.gclient.checkout()
  gclient_data = api.step_history['gclient sync'].json.output
  build_revision = gclient_data['solutions']['src/']['revision']
  # If being run as a try server, apply the CL.
  if 'rietveld' in api.properties:
    yield api.rietveld.apply_issue()
  yield api.chromium.runhooks()
  # Since performance tests aren't run on the debug builders, it isn't
  # necessary to build all of the targets there.
  build_tag = '' if is_release_build else 'debug_'
  yield api.chromium.compile(targets=['chromium_gpu_%sbuilder' % build_tag])

  # TODO(kbr): currently some properties are passed to runtest.py via
  # factory_properties in the master.cfg: generate_gtest_json,
  # show_perf_results, test_results_server, and perf_id. runtest.py
  # should be modified to take these arguments on the command line,
  # and the setting of these properties should happen in this recipe
  # instead.

  # Note: --no-xvfb is the default.
  for test in SIMPLE_TESTS_TO_RUN:
    yield api.chromium.runtests(test)

  # Former gpu_content_tests step
  args = ['--use-gpu-in-tests',
          '--generated-dir=%s' % generated_dir,
          '--reference-dir=%s' % reference_dir,
          '--build-revision=%s' % build_revision,
          '--gtest_filter=WebGLConformanceTest.*:Gpu*.*',
          '--ui-test-action-max-timeout=45000',
          '--run-manual']
  yield api.chromium.runtests('content_browsertests',
                              args,
                              annotate='gtest',
                              test_type='content_browsertests',
                              generate_json_file=True,
                              results_directory=
                                  api.path.slave_build('gtest-results',
                                      'content_browsertests'),
                              build_number=api.properties['buildnumber'],
                              builder_name=api.properties['buildername'])

  # Archive test results
  args = ['--run-id',
          '%s_%s' % (build_revision, api.properties['buildername']),
          '--generated-dir', generated_dir,
          '--gpu-reference-dir', reference_dir,
          '--gsutil', gsutil]
  yield api.python('archive_test_results',
      api.path.build('scripts', 'slave', 'chromium', \
                     'archive_gpu_pixel_test_results.py'),
      args, always_run=True)

  # WebGL conformance tests.
  # Choose a reasonable default for the location of the sandbox binary
  # on the bots.
  env = {}
  if api.platform.is_linux:
    env['CHROME_DEVEL_SANDBOX'] = '/opt/chromium/chrome_sandbox'
  # Note that the step name must end in 'test' or 'tests' in order for
  # the results to automatically show up on the flakiness dashboard.
  yield api.chromium.runtests(
      str(api.path.checkout('content', 'test', 'gpu', 'run_gpu_test')),
      ['webgl_conformance',
          '--output-format=gtest',
          '--webgl-conformance-version=1.0.1',
          '--browser=%s' % api.chromium.c.BUILD_CONFIG.lower()],
      annotate='gtest',
      name='webgl_conformance_tests',
      test_type='webgl_conformance_tests',
      generate_json_file=True,
      results_directory=
          api.path.slave_build('gtest-results', 'webgl_conformance_tests'),
      build_number=api.properties['buildnumber'],
      builder_name=api.properties['buildername'],
      python_mode=True,
      env=env)

  # Only run the performance tests on Release builds.
  if is_release_build:
    # Former gpu_frame_rate_test step
    args = ['--enable-gpu',
            '--gtest_filter=FrameRate*Test*']
    yield api.chromium.runtests('performance_ui_tests',
                                args,
                                name='gpu_frame_rate_test',
                                annotate='framerate',
                                results_url=dashboard_upload_url,
                                perf_dashboard_id='gpu_frame_rate',
                                test_type='gpu_frame_rate_test')

    # Former gpu_throughput_tests step
    args = ['--enable-gpu',
            '--gtest_filter=ThroughputTest*']
    yield api.chromium.runtests('performance_browser_tests',
                                args,
                                name='gpu_throughput_tests',
                                annotate='graphing',
                                results_url=dashboard_upload_url,
                                perf_dashboard_id='gpu_throughput',
                                test_type='gpu_throughput_tests')

    # TODO: Test is failing intermittently. Re-enable once the test is reliable.
    # http://crbug.com/298493
    # Former tab_capture_performance_tests_step
    #args = ['--enable-gpu',
    #        '--gtest_filter=TabCapturePerformanceTest*']
    #yield api.chromium.runtests('performance_browser_tests',
    #                            args,
    #                            name='tab_capture_performance_tests',
    #                            annotate='graphing',
    #                            results_url=dashboard_upload_url,
    #                            perf_dashboard_id='tab_capture_performance',
    #                            test_type='tab_capture_performance_tests')

  # TODO(kbr): after the conversion to recipes, add all GPU related
  # steps from the main waterfall, like gpu_unittests.

def GenTests(api):
  for build_config in ['Release', 'Debug']:
    for plat in ['win', 'mac', 'linux']:
      # Normal builder configuration
      base_name = '%s_%s' % (plat, build_config.lower())
      yield (
        api.test(base_name) +
        api.properties.scheduled(build_config=build_config) +
        api.platform.name(plat)
      )

      # Try server configuration
      yield (
        api.test('%s_tryserver' % base_name) +
        api.properties.tryserver(build_config=build_config) +
        api.platform.name(plat)
      )

  # Test one configuration using git mode.
  yield (
    api.test('mac_release_git') +
    api.properties.scheduled(build_config='Release', use_git=True) +
    api.platform.name('mac')
  )
