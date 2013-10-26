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
  'gpu',
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
  generated_dir = api.path.slave_build('content_gpu_data',
      'telemetry', 'generated')
  reference_dir = api.path.slave_build('content_gpu_data',
      'telemetry', 'reference')

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

  configuration = 'chromium'
  if api.gclient.is_blink_mode:
    configuration = 'blink'

  api.chromium.set_config(configuration, GIT_MODE=use_git)
  # This is needed to make GOMA work properly on Mac.
  if api.platform.is_mac:
    api.chromium.set_config(configuration + '_clang', GIT_MODE=use_git)
  api.gclient.apply_config('chrome_internal')

  # Use the default Ash and Aura settings on all bots (specifically Blink bots).
  api.chromium.c.gyp_env.GYP_DEFINES.pop('use_ash', None)
  api.chromium.c.gyp_env.GYP_DEFINES.pop('use_aura', None)

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
    yield api.rietveld.apply_issue(api.rietveld.calculate_issue_root())
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
    yield api.chromium.runtests(test, spawn_dbus=True)

  # Former gpu_content_tests step
  args = ['--use-gpu-in-tests',
          '--gtest_filter=Gpu*.*',
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
                              builder_name=api.properties['buildername'],
                              spawn_dbus=True)

  # Choose a reasonable default for the location of the sandbox binary
  # on the bots.
  env = {}
  if api.platform.is_linux:
    env['CHROME_DEVEL_SANDBOX'] = '/opt/chromium/chrome_sandbox'

  # Pixel tests.
  yield api.gpu.run_telemetry_gpu_test('pixel_test',
      args=[
          '--generated-dir=%s' % generated_dir,
          '--reference-dir=%s' % reference_dir,
          '--build-revision=%s' % build_revision,
      ])

  # Archive telemetry pixel test results
  yield api.gpu.archive_pixel_test_results('archive_pixel_test_results',
      '%s_%s_telemetry' % (build_revision, api.properties['buildername']),
      generated_dir=generated_dir,
      reference_dir=generated_dir) # This mismatch is intentional.
  # Reference images are copied into the generated directory upon failure
  # to ensure that they get archived with the correct name.

  # WebGL conformance tests.
  yield api.gpu.run_telemetry_gpu_test('webgl_conformance',
      args=[
          '--webgl-conformance-version=1.0.1'
      ])

  # Context lost tests.
  yield api.gpu.run_telemetry_gpu_test('context_lost')

  # Memory tests.
  yield api.gpu.run_telemetry_gpu_test('memory_test')

  # Only run the performance tests on Release builds.
  if is_release_build:
    # Former tab_capture_performance_tests_step
    args = ['--enable-gpu',
            '--gtest_filter=TabCapturePerformanceTest*']
    yield api.chromium.runtests('performance_browser_tests',
                                args,
                                name='tab_capture_performance_tests',
                                annotate='graphing',
                                results_url=dashboard_upload_url,
                                perf_dashboard_id='tab_capture_performance',
                                test_type='tab_capture_performance_tests',
                                spawn_dbus=True)

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

      # Blink builder configuration
      yield (
        api.test('%s_blink' % base_name) +
        api.properties.scheduled(
            build_config=build_config,
            top_of_tree_blink=True) +
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
    api.properties.git_scheduled(build_config='Release', use_git=True) +
    api.platform.name('mac')
  )

  # Test one trybot configuration with Blink issues.
  yield (
    api.test('mac_release_tryserver_blink') +
    api.properties.tryserver(
        build_config='Release',
        root='src/third_party/WebKit') +
    api.platform.name('mac')
  )
