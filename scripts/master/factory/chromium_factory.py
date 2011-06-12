# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the chromium master BuildFactory's.

Based on gclient_factory.py and adds chromium-specific steps."""

import os
import re

from buildbot.process.properties import WithProperties
from buildbot.steps import trigger

from master.factory import chromium_commands
from master.factory import gclient_factory
from master.factory.build_factory import BuildFactory

import config


class ChromiumFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the chromium master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # On valgrind bots, override the optimizer settings so we don't inline too
  # much and make the stacks harder to figure out. Use the same settings
  # on all buildbot masters to make it easier to move bots.
  MEMORY_TOOLS_GYP_DEFINES = (
    # gcc flags
    'mac_debug_optimization=1 '
    'mac_release_optimization=1 '
    'release_optimize=1 '
    'no_gc_sections=1 '
    'debug_extra_cflags="-g -fno-inline -fno-omit-frame-pointer -fno-builtin" '
    'release_extra_cflags="-g -fno-inline -fno-omit-frame-pointer '
                          '-fno-builtin" '

    # MSVS flags
    'win_debug_Optimization=1 '
    'win_debug_RuntimeChecks=0 '
    'win_debug_InlineFunctionExpansion=0 '
    'win_debug_disable_iterator_debugging=1 '

    'linux_use_tcmalloc=1 '
    'release_valgrind_build=1 '
    'werror= '
  )

  # gclient custom vars
  CUSTOM_VARS_GOOGLECODE_URL = ('googlecode_url', config.Master.googlecode_url)
  CUSTOM_VARS_WEBKIT_MIRROR = ('webkit_trunk', config.Master.webkit_trunk_url)
  # $$WK_REV$$ below will be substituted with the revision that triggered the
  # build in chromium_step.py@GClient.startVC. Use this only with builds
  # triggered by a webkit poller.
  CUSTOM_VARS_WEBKIT_LATEST = [('webkit_trunk', config.Master.webkit_trunk_url),
                               ('webkit_revision', '$$WK_REV$$')]
  # safe sync urls
  SAFESYNC_URL_CHROMIUM = 'http://chromium-status.appspot.com/lkgr'

  # gclient additional custom deps
  CUSTOM_DEPS_V8_LATEST = ('src/v8',
    'http://v8.googlecode.com/svn/branches/bleeding_edge')
  CUSTOM_DEPS_NACL_LATEST = ('src/native_client',
    'http://src.chromium.org/native_client/trunk/src/native_client')
  CUSTOM_DEPS_VALGRIND = ('src/third_party/valgrind',
     config.Master.trunk_url + '/deps/third_party/valgrind/binaries')
  CUSTOM_DEPS_TSAN_WIN = ('src/third_party/tsan',
     config.Master.trunk_url + '/deps/third_party/tsan')
  CUSTOM_DEPS_DRMEMORY = ('src/third_party/drmemory',
     config.Master.trunk_url + '/deps/third_party/drmemory')

  CUSTOM_DEPS_GYP = [
    ('src/tools/gyp', 'http://gyp.googlecode.com/svn/trunk')]

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
    '^(webkit|webkit_gpu)$':
      [('src/webkit/data/layout_tests/LayoutTests', None),
       ('src/third_party/WebKit/LayoutTests', None),]
  }

  NEEDED_COMPONENTS_INTERNAL = {
    'memory':
      [('src/data/memory_test', None)],
    'page_cycler':
      [('src/data/page_cycler', None)],
    '(selenium|chrome_frame)':
      [('src/data/selenium_core', None)],
    'tab_switching':
      [('src/data/tab_switching', None)],
    'ui':
      [('src/chrome/test/data/firefox2_profile/searchplugins', None),
       ('src/chrome/test/data/firefox2_searchplugins', None),
       ('src/chrome/test/data/firefox3_profile/searchplugins', None),
       ('src/chrome/test/data/firefox3_searchplugins', None),
       ('src/chrome/test/data/ssl/certs', None)],
    '(plugin|pyauto_functional_tests)':
      [('src/chrome/test/data/plugin', None)],
    'unit':
      [('src/chrome/test/data/osdd', None)],
    '^(webkit|test_shell)$':
      [('src/webkit/data/bmp_decoder', None),
       ('src/webkit/data/ico_decoder', None),
       ('src/webkit/data/test_shell/plugins', None),
       ('src/webkit/data/xbm_decoder', None)],
    # Unused stuff:
    'autodiscovery':
      [('src/data/autodiscovery', None)],
    'esctf':
      [('src/data/esctf', None)],
    'grit':
      [('src/tools/grit/grit/test/data', None)],
    'mozilla_js':
      [('src/data/mozilla_js_tests', None)],
  }

  # Minimal deps for running PyAuto.
  # http://dev.chromium.org/developers/pyauto
  PYAUTO_DEPS = \
      [('src/chrome/test/data',
        'http://src.chromium.org/svn/trunk/src/chrome/test/data'),
       ('src/chrome/test/pyautolib',
        'http://src.chromium.org/svn/trunk/src/chrome/test/pyautolib'),
       ('src/chrome/test/functional',
        'http://src.chromium.org/svn/trunk/src/chrome/test/functional'),
       ('src/third_party/simplejson',
        'http://src.chromium.org/svn/trunk/src/third_party/simplejson'),
       ('src/third_party/psutil',
        'http://src.chromium.org/svn/trunk/src/third_party/psutil'),
       ('src/net/tools/testserver',
        'http://src.chromium.org/svn/trunk/src/net/tools/testserver'),
       ('src/third_party/pyftpdlib',
        'http://src.chromium.org/svn/trunk/src/third_party/pyftpdlib'),
       ('src/third_party/tlslite',
        'http://src.chromium.org/svn/trunk/src/third_party/tlslite'),
       ('src/third_party/python_26',
        'http://src.chromium.org/svn/trunk/tools/third_party/python_26')]
  # Extend if we can.
  # pylint: disable=E1101
  if config.Master.trunk_internal_url:
    PYAUTO_DEPS.append(('src/chrome/test/data/plugin',
                        config.Master.trunk_internal_url +
                        '/data/chrome_plugin_tests'))
    PYAUTO_DEPS.append(('src/chrome/test/data/pyauto_private',
                        config.Master.trunk_internal_url +
                        '/data/pyauto_private'))

  def __init__(self, build_dir, target_platform=None, pull_internal=True):
    main = gclient_factory.GClientSolution(config.Master.trunk_url_src,
               needed_components=self.NEEDED_COMPONENTS,
               custom_vars_list=[self.CUSTOM_VARS_WEBKIT_MIRROR,
                                 self.CUSTOM_VARS_GOOGLECODE_URL])
    custom_deps_list = [main]
    if config.Master.trunk_internal_url_src and pull_internal:
      internal = gclient_factory.GClientSolution(
                     config.Master.trunk_internal_url_src,
                     needed_components=self.NEEDED_COMPONENTS_INTERNAL)
      custom_deps_list.append(internal)

    gclient_factory.GClientFactory.__init__(self, build_dir, custom_deps_list,
                                            target_platform=target_platform)

  def _AddTests(self, factory_cmd_obj, tests, mode=None,
                factory_properties=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}

    # This function is too crowded, try to simplify it a little.
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)
    f = factory_cmd_obj
    fp = factory_properties

    # Copy perf expectations from slave to master for use later.
    if factory_properties.get('expectations'):
      f.AddUploadPerfExpectations(factory_properties)

    # When modifying the order of the tests here, please take
    # http://build.chromium.org/buildbot/waterfall/stats into account.
    # Tests that fail more often should be earlier in the queue.

    # Check for an early bail.  Do early since this may cancel other tests.
    if R('check_lkgr'):     f.AddCheckLKGRStep()

    # Scripted checks to verify various properties of the codebase:
    if R('check_deps'):     f.AddCheckDepsStep()
    if R('check_bins'):     f.AddCheckBinsStep()
    if R('check_perms'):    f.AddCheckPermsStep()

    # Small ("module") unit tests:
    if R('base'):           f.AddBasicGTestTestStep('base_unittests', fp)
    if R('cacheinvalidation'):
      f.AddBasicGTestTestStep('cacheinvalidation_unittests', fp)
    if R('courgette'):      f.AddBasicGTestTestStep('courgette_unittests', fp)
    if R('crypto'):         f.AddBasicGTestTestStep('crypto_unittests', fp)
    if R('gfx'):            f.AddBasicGTestTestStep('gfx_unittests', fp)
    if R('googleurl'):      f.AddBasicGTestTestStep('googleurl_unittests', fp)
    if R('gpu'):            f.AddBasicGTestTestStep(
                                'gpu_unittests', fp,
                                arg_list=['--gmock_verbose=error'])
    if R('jingle'):         f.AddBasicGTestTestStep('jingle_unittests', fp)
    if R('media'):          f.AddBasicGTestTestStep('media_unittests', fp)
    if R('net'):            f.AddBasicGTestTestStep('net_unittests', fp)
    if R('plugin'):         f.AddBasicGTestTestStep('plugin_tests', fp)
    if R('printing'):       f.AddBasicGTestTestStep('printing_unittests', fp)
    if R('remoting'):       f.AddBasicGTestTestStep('remoting_unittests', fp)
    if R('test_shell'):     f.AddBasicGTestTestStep('test_shell_tests', fp)
    if R('safe_browsing'):  f.AddBasicGTestTestStep(
                                'safe_browsing_tests', fp,
                                arg_list=['--ui-test-action-max-timeout=40000'])
    if R('sandbox'):
      f.AddBasicGTestTestStep('sbox_unittests', fp)
      f.AddBasicGTestTestStep('sbox_integration_tests', fp)
      f.AddBasicGTestTestStep('sbox_validation_tests', fp)

    if R('views'):          f.AddBasicGTestTestStep('views_unittests', fp)

    # Medium-sized tests (unit and browser):
    if R('unit'):           f.AddChromeUnitTests(fp)
    if R('browser_tests'):  f.AddBrowserTests(fp)

    # Big, UI tests:
    if R('ui'):             f.AddUITests(False, fp)
    if R('ui-single'):      f.AddUITests(True, fp)
    if R('nacl_ui'):        f.AddBasicGTestTestStep('nacl_ui_tests', fp)
    if R('nacl_integration'): f.AddNaClIntegrationTestStep(fp)
    if R('nacl_sandbox'):   f.AddBasicGTestTestStep('nacl_sandbox_tests', fp)
    if R('automated_ui'):   f.AddAutomatedUiTests(fp)
    if R('interactive_ui'): f.AddBasicGTestTestStep('interactive_ui_tests', fp)
    if R('selenium'):       f.AddBasicShellStep('selenium_tests')
    if R('dom_checker'):    f.AddDomCheckerTests()
    if R('page_load'):      f.AddPageLoadTests(fp)

    if R('installer'):      f.AddInstallerTests(fp)

    # WebKit-related tests:
    if R('webkit_unit'):    f.AddBasicGTestTestStep('webkit_unit_tests', fp)
    if R('webkit'):         f.AddWebkitTests(gpu=False,
                                             factory_properties=fp)
    if R('webkit_gpu'):     f.AddWebkitTests(gpu=True,
                                             factory_properties=fp)

    # Benchmark tests:
    if R('page_cycler'):    f.AddPageCyclerTests(fp)
    if R('memory'):         f.AddMemoryTests(fp)
    if R('tab_switching'):  f.AddTabSwitchingTests(fp)
    if R('sunspider'):      f.AddSunSpiderTests(fp)
    if R('v8_benchmark'):   f.AddV8BenchmarkTests(fp)
    if R('dromaeo'):        f.AddDromaeoTests(fp)
    if R('dom_perf'):       f.AddDomPerfTests(fp)
    if R('page_cycler_http'):
      fp['http_page_cyclers'] = True
      f.AddPageCyclerTests(factory_properties=fp)
    if R('startup'):
      f.AddStartupTests(fp)
      f.AddNewTabUITests(fp)
    if R('sizes'):          f.AddSizesTests(fp)

    if R('sync_integration'):
      f.AddSyncIntegrationTests(fp)

    # GPU tests:
    if R('gpu_tests'):      f.AddGpuTests(fp)

    # ChromeFrame tests:
    if R('chrome_frame_unittests'):
      f.AddBasicGTestTestStep('chrome_frame_unittests', fp)
    if R('chrome_frame_perftests'):
      f.AddChromeFramePerfTests(fp)
    if R('chrome_frame'):
      f.AddBasicGTestTestStep('chrome_frame_net_tests', fp)
      f.AddBasicGTestTestStep('chrome_frame_unittests', fp)
      f.AddBasicGTestTestStep('chrome_frame_tests', fp)

    # Valgrind tests:
    for test in tests:
      # TODO(timurrrr): replace 'valgrind' with 'memcheck'
      #                 below and in master.chromium/master.cfg
      prefix = 'valgrind_'
      if test.startswith(prefix):
        test_name = test[len(prefix):]
        f.AddMemoryTest(test_name, "memcheck")
        continue
      # Run TSan in two-stage RaceVerifier mode.
      prefix = 'tsan_rv_'
      if test.startswith(prefix):
        test_name = test[len(prefix):]
        f.AddMemoryTest(test_name, "tsan_rv")
        continue
      prefix = 'tsan_'
      if test.startswith(prefix):
        test_name = test[len(prefix):]
        f.AddMemoryTest(test_name, "tsan")
        continue
      prefix = 'drmemory_'
      if test.startswith(prefix):
        test_name = test[len(prefix):]
        f.AddMemoryTest(test_name, "drmemory")
        continue
      prefix = 'heapcheck_'
      if test.startswith(prefix):
        test_name = test[len(prefix):]
        f.AddHeapcheckTest(test_name)
        continue


    # PyAuto functional tests.
    if R('pyauto_functional_tests'):
      f.AddPyAutoFunctionalTest('pyauto_functional_tests', suite='CONTINUOUS',
                                factory_properties=fp)
    elif R('pyauto_official_tests'):
      # Mapping from self._target_platform to a chrome-*.zip
      platmap = {'win32': 'win32',
                 'darwin': 'mac',
                 'linux2': 'lucid64bit' }
      zip_plat = platmap[self._target_platform]
      workdir = os.path.join(f.working_dir, 'chrome-' + zip_plat)
      f.AddPyAutoFunctionalTest('pyauto_functional_tests',
                                src_base='..',
                                workdir=workdir,
                                factory_properties=fp)

    # HTML5 media tag performance test using PyAuto.
    if R('media_perf'):
      platform_mapping = {
        'win32': 'win32',
        'darwin': 'mac',
        'linux2': 'lucid64bit',
      }

      zip_platform = platform_mapping[self._target_platform]
      workdir = os.path.join(f.working_dir, 'chrome-' + zip_platform)
      # Performance test should be run on virtual X buffer.
      fp['use_xvfb_on_linux'] = True
      f.AddMediaPerfTests(factory_properties=fp, src_base='..',
                          workdir=workdir)

    # ChromeDriver tests.
    if R('chromedriver_tests'):
      f.AddChromeDriverTest()
    if R('webdriver_tests'):
      f.AddWebDriverTest()

    # When adding a test that uses a new executable, update kill_processes.py.

    # Coverage tests.  Add coverage processing absoluely last, after
    # all tests have run.  Tests which run after coverage processing
    # don't get counted.
    if R('run_coverage_bundles'):
      f.AddRunCoverageBundles(fp)
    if R('process_coverage'):
      f.AddProcessCoverage(fp)

    # Add an optional set of annotated steps.
    # NOTE: This really should go last as it can be confusing if the annotator
    # isn't the last thing to run.
    if R('annotated_steps'): f.AddAnnotatedSteps(fp)


  def ChromiumFactory(self, target='Release', clobber=False, tests=None,
                      mode=None, slave_type='BuilderTester',
                      options=None, compile_timeout=1200, build_url=None,
                      project=None, factory_properties=None, gclient_deps=None):
    factory_properties = factory_properties or {}
    tests = tests or []

    if factory_properties.get("needs_valgrind"):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_VALGRIND]
    elif factory_properties.get("needs_tsan_win"):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_TSAN_WIN]
    elif factory_properties.get("needs_drmemory"):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_DRMEMORY]

    if factory_properties.get("lkgr"):
      self._solutions[0].safesync_url = self.SAFESYNC_URL_CHROMIUM

    tests_for_build = [
        re.match('^(?:valgrind_|heapcheck_)?(.*)$', t).group(1) for t in tests]
    factory = self.BuildFactory(target, clobber, tests_for_build, mode,
                                slave_type, options, compile_timeout, build_url,
                                project, factory_properties,
                                gclient_deps=gclient_deps)

    # Get the factory command object to create new steps to the factory.
    chromium_cmd_obj = chromium_commands.ChromiumCommands(factory,
                                                          target,
                                                          self._build_dir,
                                                          self._target_platform)

    # Add this archive build step.
    if factory_properties.get('archive_build'):
      chromium_cmd_obj.AddArchiveBuild(factory_properties=factory_properties)

    # Add the package source step.
    if slave_type == 'Updater':
      chromium_cmd_obj.AddPackageSource(factory_properties=factory_properties)

    # Trigger any schedulers waiting on the build to complete.
    if factory_properties.get('trigger'):
      trigger_name = factory_properties.get('trigger')
      # Propagate properties to the children if this is set in the factory.
      trigger_properties = factory_properties.get('trigger_properties', [])
      # Add an additional property if the type of the slave is NASBuilder. The
      # testers need to receive the snapshot name.
      if slave_type == 'NASBuilder':
        trigger_properties.append('snapshot')
      factory.addStep(trigger.Trigger(
          schedulerNames=[trigger_name],
          updateSourceStamp=False,
          waitForFinish=False,
          set_properties={'parentname': WithProperties('%(buildername)s')},
          copy_properties=trigger_properties))


    # Start the crash handler process.
    if ((self._target_platform == 'win32' and slave_type != 'Builder' and
         self._build_dir == 'src/chrome') or
        factory_properties.get('start_crash_handler')):
      chromium_cmd_obj.AddRunCrashHandler()

    # Trigger the reliability tests.
    if 'reliability' in tests:
      factory.addStep(trigger.Trigger(schedulerNames=['reliability'],
                                      waitForFinish=False))
    if 'reliability_linux' in tests:
      factory.addStep(trigger.Trigger(schedulerNames=['reliability_linux'],
                                      waitForFinish=False))

    # Add all the tests.
    self._AddTests(chromium_cmd_obj, tests, mode, factory_properties)

    if factory_properties.get('process_dumps'):
      chromium_cmd_obj.AddProcessDumps()

    test_parity_platform = factory_properties.get('test_parity_platform')
    if test_parity_platform:
      chromium_cmd_obj.AddSendTestParityStep(test_parity_platform)

    # Append any post steps needed by the BuildFactory.
    self.PostBuildFactory(factory, target=target, slave_type=slave_type,
                          factory_properties=factory_properties)
    return factory

  def TargetTestsFactory(self, timeout=60*60, verbose=False,
                         factory_properties=None):
    factory = self.BaseFactory()
    cmd_obj = chromium_commands.ChromiumCommands(factory,
                                                 'Release', '',
                                                 self._target_platform)
    cmd_obj.AddTargetTests(timeout, verbose, factory_properties)
    return factory

  def ReliabilityTestsFactory(self, platform='win'):
    """Create a BuildFactory to run a reliability slave."""
    factory = BuildFactory({})
    cmd_obj = chromium_commands.ChromiumCommands(factory,
                                                 'Release', '',
                                                 self._target_platform)
    cmd_obj.AddUpdateScriptStep()
    cmd_obj.AddReliabilityTests(platform=platform)
    return factory

  def ChromiumV8LatestFactory(self, target='Release', clobber=False, tests=None,
                              mode=None, slave_type='BuilderTester',
                              options=None, compile_timeout=1200,
                              build_url=None, project=None,
                              factory_properties=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_V8_LATEST]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumNativeClientLatestFactory(
      self, target='Release', clobber=False, tests=None, mode=None,
      slave_type='BuilderTester', options=None, compile_timeout=1200,
      build_url=None, project=None, factory_properties=None,
      on_nacl_waterfall=True, use_chrome_lkgr=True):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_NACL_LATEST]
    self._solutions[0].safesync_url = self.SAFESYNC_URL_CHROMIUM
    # Add an extra frivilous checkout of part of NativeClient when it is built
    # on the # NativeClient waterfall. This way, console view gets revision
    # numbers that it can make sense of.
    if on_nacl_waterfall:
      self._solutions.insert(0, gclient_factory.GClientSolution(
          self.CUSTOM_DEPS_NACL_LATEST[1] + '/build',
          name='build'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumWebkitLatestFactory(self, target='Release', clobber=False,
                                  tests=None, mode=None,
                                  slave_type='BuilderTester', options=None,
                                  compile_timeout=1200, build_url=None,
                                  project=None, factory_properties=None):
    self._solutions[0].custom_vars_list = self.CUSTOM_VARS_WEBKIT_LATEST
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumGYPLatestFactory(self, target='Debug', clobber=False, tests=None,
                               mode=None, slave_type='BuilderTester',
                               options=None, compile_timeout=1200,
                               build_url=None, project=None,
                               factory_properties=None, gyp_format=None):

    if tests is None:
      tests = ['unit']

    if gyp_format:
      # Set GYP_GENERATORS in the environment used to execute
      # gclient so we get the right build tool configuration.
      if factory_properties is None:
        factory_properties = {}
      gclient_env = factory_properties.get('gclient_env', {})
      gclient_env['GYP_GENERATORS'] = gyp_format
      factory_properties['gclient_env'] = gclient_env

      # And tell compile.py what build tool to use.
      if options is None:
        options = []
      options.append('--build-tool=' + gyp_format)

    self._solutions[0].custom_deps_list = self.CUSTOM_DEPS_GYP
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumArmuFactory(self, target='Release', clobber=False, tests=None,
                          mode=None, slave_type='BuilderTester', options=None,
                          compile_timeout=1200, build_url=None, project=None,
                          factory_properties=None):
    self._project = 'webkit_armu.sln'
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_V8_LATEST]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumOSFactory(self, target='Release', clobber=False, tests=None,
                        mode=None, slave_type='BuilderTester', options=None,
                        compile_timeout=1200, build_url=None, project=None,
                        factory_properties=None):
    # Make sure the solution is not already there.
    if 'cros_deps' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/src/tools/cros.DEPS', name='cros_deps'))

    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def CEFFactory(self, target='Release', clobber=False, tests=None, mode=None,
                 slave_type='BuilderTester', options=None, compile_timeout=1200,
                 build_url=None, project=None, factory_properties=None):
    self._solutions.append(gclient_factory.GClientSolution(
        'http://chromiumembedded.googlecode.com/svn/trunk',
        'src/cef'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumBranchFactory(
      self, target='Release', clobber=False, tests=None, mode=None,
      slave_type='BuilderTester', options=None, compile_timeout=1200,
      build_url=None, project=None, factory_properties=None,
      trunk_src_url=None):
    self._solutions = [gclient_factory.GClientSolution(trunk_src_url, 'src')]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumQAFactory(self, target='Release', clobber=False, tests=None,
                        mode=None, slave_type='Tester', options=None,
                        compile_timeout=1200, build_url=None, project=None,
                        factory_properties=None):

    # Clear existing solutions so by default we don't sync the universe.
    self._solutions = []
    # When syncing on a branch, don't sync these components on a branch.
    avoid_branch_sync_component = ['python_26', 'chrome_plugin_tests',
                                   'pyauto_private']
    # Sync only what we need (e.g. PyAuto test files).
    for name, url in self.PYAUTO_DEPS:
      # If branch is available, replace 'trunk' to 'branches/<BRANCH>'
      # in a url.
      if factory_properties and factory_properties.get('branch'):
        if not url.split('/')[-1] in avoid_branch_sync_component:
          url = url.replace('trunk',
                            'branches/' + str(factory_properties['branch']))

      # Yes, url goes first, which is different from how most people
      # lay out their .gclient.
      # Prepend to make sure chrome/src is not created by a DEPS pull.
      self._solutions.append(gclient_factory.GClientSolution(url, name))

    # Instead of calling self.ChromiumFactory(), we copy a few of it's
    # lines (e.g. everything from here on other than
    # AddDownloadAndExtractOfficialBuild()).
    factory = self.BuildFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)
    chromium_cmd_obj = chromium_commands.ChromiumCommands(factory,
                                                          target,
                                                          self._build_dir,
                                                          self._target_platform)

    qa_identifier = factory_properties.get('qa_identifier')
    if factory_properties.get('branch'):
      chromium_cmd_obj.AddDownloadAndExtractOfficialBuild(qa_identifier,
          factory_properties['branch'])
    else:
      chromium_cmd_obj.AddDownloadAndExtractOfficialBuild(qa_identifier)

    # crash_service.exe doesn't fire up on its own because we have the
    # binaries in chrome-win32 dir (not in the default src/chrome/Release).
    # Fire it by force.
    if self._target_platform == 'win32':
      chromium_cmd_obj.AddRunCrashHandler(build_dir='chrome-win32', target='.')
    self._AddTests(chromium_cmd_obj, tests, mode, factory_properties)
    return factory

  def ChromiumGPUFactory(self, target='Release', clobber=False, tests=None,
                         mode=None, slave_type='Tester', options=None,
                         compile_timeout=1200, build_url=None, project=None,
                         factory_properties=None):
    # Make sure the solution is not already there.
    if 'gpu_reference.DEPS' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          'http://src.chromium.org/svn/trunk/deps/gpu_reference/' +
              'gpu_reference.DEPS',
          'gpu_reference.DEPS'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)
