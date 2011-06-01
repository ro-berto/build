# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds chromium-specific commands."""

import logging
import os
import re

from buildbot.process.properties import WithProperties
from buildbot.steps import shell
from buildbot.steps.transfer import FileUpload

import config
from common import chromium_utils
from master import chromium_step
from master.factory import commands

from master.log_parser import archive_command
from master.log_parser import gtest_command
from master.log_parser import process_log
from master.log_parser import retcode_command
from master.log_parser import webkit_test_command

class ChromiumCommands(commands.FactoryCommands):
  """Encapsulates methods to add chromium commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    # Where the chromium slave scritps are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', '..', '..',
                                             'build_internal', 'scripts',
                                             'slave')

    # Create smaller name for the functions and vars to siplify the code below.
    J = self.PathJoin
    s_dir = self._chromium_script_dir
    p_dir = self._private_script_dir

    self._process_dumps_tool = self.PathJoin(self._script_dir,
                                             'process_dumps.py')

    # Scripts in the chromium scripts dir.
    self._differential_installer_tool = J(s_dir,  'differential_installer.py')
    self._process_coverage_tool = J(s_dir, 'process_coverage.py')
    self._layout_archive_tool = J(s_dir, 'archive_layout_test_results.py')
    self._package_source_tool = J(s_dir, 'package_source.py')
    self._crash_handler_tool = J(s_dir, 'run_crash_handler.py')
    self._upload_parity_tool = J(s_dir, 'upload_parity_data.py')
    self._target_tests_tool = J(s_dir, 'target-tests.py')
    self._layout_test_tool = J(s_dir, 'layout_test_wrapper.py')
    self._archive_coverage = J(s_dir, 'archive_coverage.py')
    self._gpu_archive_tool = J(s_dir, 'archive_gpu_pixel_test_results.py')
    self._crash_dump_tool = J(s_dir, 'archive_crash_dumps.py')
    self._dom_perf_tool = J(s_dir, 'dom_perf.py')
    self._archive_tool = J(s_dir, 'archive_build.py')
    self._sizes_tool = J(s_dir, 'sizes.py')
    self._check_lkgr_tool = J(s_dir, 'check_lkgr.py')

    # Scripts in the private dir.
    self._reliability_tool = J(p_dir, 'reliability_tests.py')
    self._reliability_data = J(p_dir, 'data', 'reliability')
    self._download_and_extract_official_tool = self.PathJoin(
        p_dir, 'get_official_build.py')

    # These scripts should be move to the script dir.
    self._check_deps_tool = J('src', 'tools', 'checkdeps', 'checkdeps.py')
    self._check_bins_tool = J('src', 'tools', 'checkbins', 'checkbins.py')
    self._check_perms_tool = J('src', 'tools', 'checkperms', 'checkperms.py')
    self._posix_memory_tests_runner = J('src', 'tools', 'valgrind',
                                        'chrome_tests.sh')
    self._win_memory_tests_runner = J('src', 'tools', 'valgrind',
                                      'chrome_tests.bat')
    self._heapcheck_tool = J('src', 'tools', 'heapcheck', 'chrome_tests.sh')
    self._annotated_steps = J('src', 'build', 'buildbot_annotated_steps.py')
    self._nacl_integration_tester_tool = J(
        'src', 'chrome', 'test', 'nacl_test_injection',
        'buildbot_nacl_integration.py')
    # chrome_staging directory, relative to the build directory.
    self._staging_dir = self.PathJoin('..', 'chrome_staging')

    # The _update_scripts_command will be run in the _update_scripts_dir to
    # udpate the slave's own script checkout.
    self._update_scripts_dir = '..'
    self._update_scripts_command = [
        chromium_utils.GetGClientCommand(self._target_platform),
        'sync', '--verbose']

  def AddArchiveStep(self, data_description, base_url, link_text, command,
                     more_link_url = None, more_link_text = None):
    step_name = ('archive_%s' % data_description).replace(' ', '_')
    self._factory.addStep(archive_command.ArchiveCommand,
                          name=step_name,
                          timeout=600,
                          description='archiving %s' % data_description,
                          descriptionDone='archived %s' % data_description,
                          base_url=base_url,
                          link_text=link_text,
                          more_link_url=more_link_url,
                          more_link_text=more_link_text,
                          command=command)

  def AddUploadPerfExpectations(self, factory_properties=None):
    """Adds a step to the factory to upload perf_expectations.json to the
    master.
    """
    perf_id = factory_properties.get('perf_id')
    if not perf_id:
      logging.error("Error: cannot upload perf expectations: perf_id is unset")
      return
    slavesrc = 'src/tools/perf_expectations/perf_expectations.json'
    masterdest = ('../../scripts/master/log_parser/perf_expectations/%s.json' %
                  perf_id)

    self._factory.addStep(FileUpload(slavesrc=slavesrc,
                                     masterdest=masterdest))

  def AddArchiveBuild(self, mode='dev', show_url=True, factory_properties=None):
    """Adds a step to the factory to archive a build."""

    extra_archive_paths = factory_properties.get('extra_archive_paths')
    use_build_number = factory_properties.get('use_build_number', False)

    if show_url:
      url = _GetArchiveUrl('snapshots')
      text = 'download'
    else:
      url = None
      text = None

    cmd = [self._python, self._archive_tool,
           '--target', self._target,
           '--build-dir', self._build_dir,
           '--mode', mode]
    if extra_archive_paths:
      cmd.extend(['--extra-archive-paths', extra_archive_paths])
    if use_build_number:
      cmd.extend(['--build-number', WithProperties("%(buildnumber)s")])

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self.AddArchiveStep(data_description='build', base_url=url, link_text=text,
                        command=cmd)

  def AddPackageSource(self, factory_properties=None):
    """Adds a step to the factory to package and upload the source directory."""

    cmd = [self._python, self._package_source_tool,
           '--build-dir', self._build_dir]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self._factory.addStep(archive_command.ArchiveCommand,
                          name='package_source',
                          timeout=600,
                          description='packaging source',
                          descriptionDone='packaged source',
                          base_url=None,
                          link_text=None,
                          more_link_url=None,
                          more_link_text=None,
                          command=cmd)

  def AddCheckDepsStep(self):
    cmd = [self._python, self._check_deps_tool,
           '--root', self._repository_root]
    self.AddTestStep(shell.ShellCommand, 'check_deps', cmd)

  def AddCheckBinsStep(self):
    build_dir = os.path.join(self._build_dir, self._target)
    cmd = [self._python, self._check_bins_tool, build_dir]
    self.AddTestStep(shell.ShellCommand, 'check_bins', cmd)

  def AddCheckPermsStep(self):
    cmd = [self._python, self._check_perms_tool,
           '--root', self._repository_root]
    self.AddTestStep(shell.ShellCommand, 'check_perms', cmd)

  def AddCheckLKGRStep(self):
    """Check LKGR; if unchanged, cancel the build.

    Unlike other "test step" commands, this one can cancel the build
    while still keeping it green.

    Note we use "." as a root (which is the same as self.working_dir)
    to make sure a clobber step deletes the saved lkgr file.
    """
    cmd = [self._python, self._check_lkgr_tool, '--root', '.']
    self.AddTestStep(commands.CanCancelBuildShellCommand,
                     'check lkgr and stop build if unchanged',
                     cmd)

  def GetPageCyclerCommand(self, test_name, http):
    """Returns a command list to call the _test_tool on the page_cycler
    executable, with the appropriate GTest filter and additional arguments.
    """
    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]
    if http:
      test_type = 'Http'
      cmd.extend(['--with-httpd', self.PathJoin('src', 'data', 'page_cycler')])
    else:
      test_type = 'File'
    cmd.extend([self.GetExecutableName('page_cycler_tests'),
                '--gtest_filter=PageCycler*.%s%s:PageCycler*.*_%s%s' % (
                    test_name, test_type, test_name, test_type)])
    return cmd

  def AddPageCyclerTests(self, factory_properties=None):
    """Adds a step to the factory to run the page-cycler tests."""

    tests = [
      {'name': 'moz'},
      {'name': 'morejs', 'http': False},
      {'name': 'intl1', 'http': False, 'target': 'Release'},
      {'name': 'intl2', 'http': False, 'target': 'Release'},
      {'name': 'bloat', 'http': True, 'target': 'Release'},
      {'name': 'dhtml', 'http': False, 'target': 'Release'},
      {'name': 'database', 'http': False, 'title': 'Database*'},
      {'name': 'indexeddb', 'http': False, 'title': 'IndexedDB*'},
    ]

    factory_properties = factory_properties or {}
    # If 'http_page_cyclers' is set to True in factory_properties, launch an
    # httpd server and run the Httpd tests. Otherwise, run the File tests.
    # (These names are used in the GTest filters and correspond to test names
    # in page_cycler_tests.)
    http_page_cyclers = factory_properties.get('http_page_cyclers')

    for test in tests:
      # Some tests should only be run in http or file mode.
      if test.get('http', False) and not http_page_cyclers:
        continue
      if not test.get('http', True) and http_page_cyclers:
        continue

      # Some tests should only be run for a specific target.
      if test.get('target', self._target) != self._target:
        continue

      # Set the different names for this test.
      test['command_name'] = test['name'].capitalize()
      test['perf_name'] = test['name']
      if http_page_cyclers:
        test['perf_name'] += '-http'
      test['step_name'] = 'page_cycler_%s' % test['perf_name']

      # Derive the class from the factory, name, and log processor.
      test['class'] = self.GetPerfStepClass(
                          factory_properties, test['perf_name'],
                          process_log.GraphingPageCyclerLogProcessor)

      # Get the test's command.
      cmd = self.GetPageCyclerCommand(
                test.get('title', test['command_name']), http_page_cyclers)

      # Add the test step to the factory.
      self.AddTestStep(test['class'], test['step_name'], cmd)

  def AddStartupTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'startup',
                              process_log.GraphingLogProcessor)

    test_list = 'StartupTest.*:ShutdownTest.*'
    # We don't need to run the Reference tests in debug mode.
    if self._target == 'Debug':
      test_list += ':-*.*Ref*'
    options = ['--gtest_filter=%s' % test_list]

    cmd = self.GetTestCommand('startup_tests', options)
    self.AddTestStep(c, 'startup_test', cmd)

  def AddMemoryTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'memory',
                              process_log.GraphingLogProcessor)

    self.AddTestStep(c, 'memory_test', self.GetTestCommand('memory_test'))

  def AddNewTabUITests(self, factory_properties=None):
    factory_properties = factory_properties or {}

    # Cold tests
    c = self.GetPerfStepClass(factory_properties, 'new-tab-ui-cold',
                              process_log.GraphingLogProcessor)

    options = ['--gtest_filter=NewTabUIStartupTest.*Cold']
    cmd = self.GetTestCommand('startup_tests', options)
    self.AddTestStep(c, 'new_tab_ui_cold_test', cmd)

    # Warm tests
    c = self.GetPerfStepClass(factory_properties, 'new-tab-ui-warm',
                              process_log.GraphingLogProcessor)

    options = ['--gtest_filter=NewTabUIStartupTest.*Warm']
    cmd = self.GetTestCommand('startup_tests', options)
    self.AddTestStep(c, 'new_tab_ui_warm_test', cmd)

  def AddTabSwitchingTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'tab-switching',
                              process_log.GraphingLogProcessor)

    options = ['--gtest_filter=TabSwitchingUITest.*', '-enable-logging',
               '-dump-histograms-on-exit', '-log-level=0']

    cmd = self.GetTestCommand('tab_switching_test', options)
    self.AddTestStep(c, 'tab_switching_test', cmd)

  def AddSizesTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'sizes',
                              process_log.GraphingLogProcessor)
    cmd = [self._python, self._sizes_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    self.AddTestStep(c, 'sizes', cmd)

  def AddTargetTests(self, timeout=None, verbose=None, factory_properties=None):
    factory_properties = factory_properties or {}

    class PerformanceGTestLogProcessor:
      """
      A shotgun-marriage class to get test results graphed by perf
      but log failures analyzed like GTest with "GTestFullCommand"
      test abbreviations.
      """
      def __init__(self, *args, **kw):
        self.graphing = process_log.GraphingLogProcessor(*args, **kw)
        self.gtest = gtest_command.GTestFullCommand(*args, **kw)

      def ReportLink(self, *args, **kw):
        return self.graphing.ReportLink(*args, **kw)
      def Process(self, *args, **kw):
        return self.graphing.Process(*args, **kw)

      def TestAbbrFromTestID(self, *args, **kw):
        return self.gtest.TestAbbrFromTestID(*args, **kw)
      def createSummary(self, *args, **kw):
        return self.gtest.createSummary(*args, **kw)


    c = self.GetPerfStepClass(factory_properties, 'targets',
                              PerformanceGTestLogProcessor)

    command = [self._python, self._target_tests_tool]
    if verbose:
      command.append('-v')
    if timeout is None:
      # One hour default, sufficient for all target builds as of July 2009.
      timeout = 60 * 60
    self.AddTestStep(c, 'targets', command, timeout=timeout)

  def AddSunSpiderTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'sunspider',
                              process_log.GraphingLogProcessor)

    options = ['--gtest_filter=SunSpider*.*', '--gtest_print_time',
               '--run-sunspider']
    cmd = self.GetTestCommand('ui_tests', arg_list=options)
    self.AddTestStep(c, 'sunspider_test', cmd)

  def AddV8BenchmarkTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'v8_benchmark',
                              process_log.GraphingLogProcessor)

    options = ['--gtest_filter=V8Benchmark*.*', '--gtest_print_time',
               '--run-v8-benchmark']
    cmd = self.GetTestCommand('ui_tests', arg_list=options)
    self.AddTestStep(c, 'v8_benchmark_test', cmd)

  def AddDromaeoTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    tests = ['DOMCore', 'JSLib']
    for test in tests:
      cls = self.GetPerfStepClass(factory_properties,
                                  'dromaeo_%s' % test.lower(),
                                  process_log.GraphingLogProcessor)
      options = ['--gtest_filter=Dromaeo*Test.%sPerf' % test,
                 '--gtest_print_time', '--run-dromaeo-benchmark']
      cmd = self.GetTestCommand('ui_tests', arg_list=options)
      self.AddTestStep(cls, 'dromaeo_%s_test' % test.lower(), cmd)

  def AddDomPerfTests(self, factory_properties):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'dom_perf',
                              process_log.GraphingLogProcessor)

    cmd = [self._python, self._dom_perf_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]
    self.AddTestStep(c, 'dom_perf', cmd)

  def AddChromeFramePerfTests(self, factory_properties):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'chrome_frame_perf',
                              process_log.GraphingLogProcessor)

    cmd = self.GetTestCommand('chrome_frame_perftests')
    self.AddTestStep(c, 'chrome_frame_perf', cmd)

  # Reliability sanity tests.
  def AddAutomatedUiTests(self, factory_properties=None):
    arg_list = ['--gtest_filter=-AutomatedUITest.TheOneAndOnlyTest']
    self.AddBasicGTestTestStep('automated_ui_tests', factory_properties,
                               arg_list=arg_list)

  def AddPageLoadTests(self, factory_properties=None):
    arg_list = ['--gtest_filter=PageLoad.Reliability']
    self.AddBasicGTestTestStep('ui_tests', factory_properties,
                               arg_list=arg_list)

  def AddReliabilityTests(self, platform='win'):
    cmd_1 = ['python', self._reliability_tool, '--platform', platform,
             '--data-dir', self._reliability_data, '--mode', '0']
    cmd_2 = ['python', self._reliability_tool, '--platform', platform,
             '--data-dir', self._reliability_data, '--mode', '1']
    self.AddTestStep(retcode_command.ReturnCodeCommand,
                     'reliability: complete result of previous build', cmd_1)
    self.AddTestStep(retcode_command.ReturnCodeCommand,
                     'reliability: partial result of current build', cmd_2)

  def AddInstallerTests(self, factory_properties):
    if self._target_platform == 'win32':
      self.AddBasicGTestTestStep('installer_util_unittests', factory_properties)
      if (self._target == 'Release' and
          not factory_properties.get('disable_mini_installer_test')):
        self.AddBasicGTestTestStep('mini_installer_test', factory_properties,
                                   arg_list=['-clean'])

  def AddChromeUnitTests(self, factory_properties):
    self.AddBasicGTestTestStep('ipc_tests', factory_properties)
    self.AddBasicGTestTestStep('sync_unit_tests', factory_properties)
    self.AddBasicGTestTestStep('unit_tests', factory_properties)
    self.AddBasicGTestTestStep('app_unittests', factory_properties)
    self.AddBasicGTestTestStep('gfx_unittests', factory_properties)
    if self._target_platform == 'win32':
      self.AddBasicGTestTestStep('views_unittests', factory_properties)

  def AddSyncIntegrationTests(self, factory_properties):
    options = ['--test-terminate-timeout=120000']

    self.AddBasicGTestTestStep('sync_integration_tests', factory_properties, '',
                               options)

  def AddBrowserTests(self, factory_properties=None):
    description = ''
    options = ['--lib=browser_tests']

    total_shards = factory_properties.get('browser_total_shards')
    shard_index = factory_properties.get('browser_shard_index')

    self.AddBasicGTestTestStep('browser_tests', factory_properties,
                               description, options, total_shards=total_shards,
                               shard_index=shard_index)

  def AddUITests(self, single_process, factory_properties=None):
    description = ''
    options = []

    if single_process:
      options = ['--single-process']
      description = ' (--single-process)'

    total_shards = factory_properties.get('ui_total_shards')
    shard_index = factory_properties.get('ui_shard_index')

    self.AddBasicGTestTestStep('ui_tests', factory_properties,
                               description, options, total_shards=total_shards,
                               shard_index=shard_index)

  def AddOmniboxTests(self, factory_properties=None):
    # This is not a UI unit test.  Rather, it is a long-running test that
    # scores Omnibox results.  It's part of ui_tests because it uses much
    # of the UI test framework, so putting it there made more sense than
    # creating a new project.  This test needs a special command-line switch
    # in order to run, which prevents it from running by default.
    options = ['--gtest_filter=OmniboxTest.Measure',
               '--run_omnibox_test']
    self.AddBasicGTestTestStep('ui_tests', factory_properties,
                               'omnibox_tests', options)

  def AddDomCheckerTests(self):
    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    cmd.extend(['--with-httpd',
                self.PathJoin('src', 'chrome', 'test', 'data')])

    cmd.extend([self.GetExecutableName('ui_tests'),
                '--gtest_filter=DomCheckerTest.*',
                '--gtest_print_time',
                '--run-dom-checker-test'])

    self.AddTestStep(shell.ShellCommand, 'dom_checker_tests', cmd)

  def AddMemoryTest(self, test_name, tool_name, timeout=1200):
    # TODO(timurrrr): merge this with Heapcheck runner. http://crbug.com/45482
    build_dir = os.path.join(self._build_dir, self._target)
    if self._target_platform == 'darwin':  # Mac bins reside in src/xcodebuild
      build_dir = os.path.join(os.path.dirname(self._build_dir), 'xcodebuild',
                               self._target)
    elif self._target_platform == 'linux2':  # Linux bins in src/sconsbuild
      build_dir = os.path.join(os.path.dirname(self._build_dir), 'sconsbuild',
                               self._target)
    elif self._target_platform == 'win32':  # Windows binaries are in src/build
      build_dir = os.path.join(os.path.dirname(self._build_dir), 'build',
                               self._target)

    cmd = [self._python, self._test_tool, '--run-shell-script',
           '--target', self._target, '--build-dir', self._build_dir]
    matched = re.search(r'_([0-9]*)_of_([0-9]*)$', test_name)
    if matched:
      test_name = test_name[0:matched.start()]
      shard = int(matched.group(1))
      numshards = int(matched.group(2))
      cmd.extend(['--shard-index', str(shard),
                  '--total-shards', str(numshards)])

    # Memory tests runner script path is relative to build_dir.
    if self._target_platform != 'win32':
      runner = os.path.join('..', '..', '..', self._posix_memory_tests_runner)
    else:
      runner = os.path.join('..', '..', '..', self._win_memory_tests_runner)
    cmd.extend([runner,
                '--build_dir', build_dir,
                '--test', test_name,
                '--tool', tool_name])

    test_name = 'memory test: %s' % test_name
    self.AddTestStep(gtest_command.GTestFullCommand, test_name, cmd,
                     timeout=timeout)

  def AddHeapcheckTest(self, test_name, timeout=1200):
    build_dir = os.path.join(self._build_dir, self._target)
    if self._target_platform == 'linux2':  # Linux bins in src/sconsbuild
      build_dir = os.path.join(os.path.dirname(self._build_dir), 'sconsbuild',
                               self._target)

    cmd = [self._python, self._test_tool, '--run-shell-script',
           '--target', self._target, '--build-dir', self._build_dir]
    matched = re.search(r'_([0-9]*)_of_([0-9]*)$', test_name)
    if matched:
      test_name = test_name[0:matched.start()]
      shard = int(matched.group(1))
      numshards = int(matched.group(2))
      cmd.extend(['--shard-index', str(shard),
                  '--total-shards', str(numshards)])

    # Heapcheck script path is relative to build_dir.
    heapcheck_tool = os.path.join('..', '..', '..', self._heapcheck_tool)
    cmd.extend([heapcheck_tool,
                '--build_dir', build_dir,
                '--test', test_name])

    test_name = 'heapcheck test: %s' % test_name
    self.AddTestStep(gtest_command.GTestFullCommand, test_name, cmd,
                     timeout=timeout)

  def _AddBasicPythonTest(self, test_name, script, args=None, timeout=1200):
    args = args or []
    J = self.PathJoin
    if self._target_platform == 'win32':
      py26 = J('src', 'third_party', 'python_26', 'python_slave.exe')
      test_cmd = ['cmd', '/C'] + [py26, script] + args
    elif self._target_platform == 'darwin':
      test_cmd = ['python2.6', script] + args
    elif self._target_platform == 'linux2':
      # Run thru runtest.py on linux to launch virtual x server
      test_cmd = self.GetTestCommand('/usr/local/bin/python2.6',
                                     [script] + args)

    self.AddTestStep(retcode_command.ReturnCodeCommand,
                     test_name,
                     test_cmd,
                     timeout=timeout)

  def AddChromeDriverTest(self, timeout=1200):
    J = self.PathJoin
    script = J('src', 'chrome', 'test', 'webdriver',
               'chromedriver_tests.py')
    self._AddBasicPythonTest('chromedriver_tests', script, timeout=timeout)

  def AddWebDriverTest(self, timeout=1200):
    J = self.PathJoin
    script = J('src', 'chrome', 'test', 'webdriver',
               'run_webdriver_tests.py')
    self._AddBasicPythonTest('webdriver_tests', script, timeout=timeout)

  def AddPyAutoFunctionalTest(self, test_name, timeout=1200,
                              workdir=None,
                              src_base=None,
                              suite=None,
                              factory_properties=None):
    """Adds a step to run PyAuto functional tests.

    Args:
      workdir: the working dir for this step
      src_base: relative path (from workdir) to src. Not needed if workdir is
                'build' (the default)

    """
    factory_properties = factory_properties or {}
    J = self.PathJoin
    pyauto_script = J('src', 'chrome', 'test', 'functional',
                      'pyauto_functional.py')
    # in case a '..' prefix is needed
    if src_base:
      pyauto_script = J(src_base, pyauto_script)

    pyauto_functional_cmd = ['python', pyauto_script, '-v']
    if self._target_platform == 'win32':
      pyauto_functional_cmd = self.GetPythonTestCommand(pyauto_script, ['-v'])
    elif self._target_platform == 'darwin':
      pyauto_functional_cmd = self.GetTestCommand('/usr/bin/python2.5',
                                                  [pyauto_script, '-v'])
    elif (self._target_platform == 'linux2' and
          factory_properties.get('use_xvfb_on_linux')):
      # Run thru runtest.py on linux to launch virtual x server
      pyauto_functional_cmd = self.GetTestCommand('/usr/bin/python',
                                                  [pyauto_script, '-v'])

    if src_base:  # Adjust runtest.py path if needed.
      pyauto_functional_cmd[1] = J(src_base, pyauto_functional_cmd[1])
    if suite:
      pyauto_functional_cmd.append('--suite=%s' % suite)
    self.AddTestStep(retcode_command.ReturnCodeCommand,
                     test_name,
                     pyauto_functional_cmd,
                     env={'PYTHONPATH': '.'},
                     workdir=workdir,
                     timeout=timeout)

  def AddWebkitTests(self, gpu, factory_properties=None):
    """Adds a step to the factory to run the WebKit layout tests.

    Args:
      gpu: if True, run the GPU-acclerated variant of the tests.
      with_pageheap: if True, page-heap checking will be enabled for test_shell
      test_timeout: buildbot timeout for the test step
      archive_timeout: buildbot timeout for archiving the test results and
          crashes, if requested
      archive_results: whether to archive the test results
      archive_crashes: whether to archive crash reports resulting from the
          tests
      test_results_server: If specified, upload results json files to test
          results server
    """
    factory_properties = factory_properties or {}
    with_pageheap = factory_properties.get('webkit_pageheap')
    archive_results = factory_properties.get('archive_webkit_results')
    layout_part = factory_properties.get('layout_part')
    test_results_server = factory_properties.get('test_results_server')
    platform = factory_properties.get('layout_test_platform')
    enable_hardware_gpu = factory_properties.get('enable_hardware_gpu')

    if gpu:
      if platform:
        platform = platform.replace('chromium', 'chromium-gpu')
      else:
        platform = 'chromium-gpu'
      builder_name = '%(buildername)s - GPU'
      result_str = 'gpu results'
      test_name = 'webkit_gpu_tests'
    else:
      builder_name = '%(buildername)s'
      result_str = 'results'
      test_name = 'webkit_tests'

    pageheap_description = ''
    if with_pageheap:
      pageheap_description = ' (--enable-pageheap)'

    webkit_result_dir = '/'.join(['..', '..', 'layout-test-results'])

    cmd = [self._python, self._layout_test_tool,
           '--target', self._target,
           '--build-type', 'v8',
           '-o', webkit_result_dir,
           '--build-dir', self._build_dir,
           '--build-number', WithProperties("%(buildnumber)s"),
           '--builder-name', WithProperties(builder_name),]

    if layout_part:
      cmd.extend(['--run-part', layout_part])

    if with_pageheap:
      cmd.append('--enable-pageheap')

    if test_results_server:
      cmd.extend(['--test-results-server', test_results_server])
    if platform:
      cmd.extend(['--platform', platform])

    if enable_hardware_gpu:
      cmd.extend(['--options=--enable-hardware-gpu'])

    self.AddTestStep(webkit_test_command.WebKitCommand,
                     test_name=test_name,
                     test_description=pageheap_description,
                     test_command=cmd)

    if archive_results:
      cmd = [self._python, self._layout_archive_tool,
             '--results-dir', webkit_result_dir,
             '--build-dir', self._build_dir,
             '--build-number', WithProperties("%(buildnumber)s"),
             '--builder-name', WithProperties(builder_name),]

      cmd = self.AddBuildProperties(cmd)
      cmd = self.AddFactoryProperties(factory_properties, cmd)

      self.AddArchiveStep(
          data_description='webkit_tests ' + result_str,
          base_url=_GetArchiveUrl('layout_test_results'),
          link_text='layout test ' + result_str,
          command=cmd)

  def AddRunCrashHandler(self, build_dir=None, target=None):
    build_dir = build_dir or self._build_dir
    target = target or self._target
    cmd = [self._python, self._crash_handler_tool,
           '--build-dir', build_dir,
           '--target', target]
    self.AddTestStep(shell.ShellCommand, 'start_crash_handler', cmd)

  def AddProcessDumps(self):
    cmd = [self._python, self._process_dumps_tool,
           '--build-dir', self._build_dir,
           '--target', self._target]
    self.AddTestStep(shell.ShellCommand, 'process_dumps', cmd)

  def AddRunCoverageBundles(self, factory_properties=None):
    # If updating this command, update the mirror of it in chrome_tests.gypi.
    cmd = [self._python,
           os.path.join('src', 'tools', 'code_coverage', 'coverage_posix.py'),
           '--build-dir',
           self._build_dir,
           '--target',
           self._target,
           '--src_root',
           '.',
           '--bundles', 'coverage_bundles.py']
    self.AddTestStep(shell.ShellCommand, 'run_coverage_bundles', cmd)

  def AddProcessCoverage(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'coverage',
                              process_log.GraphingLogProcessor)

    cmd = [self._python, self._process_coverage_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    self.AddTestStep(c, 'process_coverage', cmd)

    # Map the perf ID to the coverage subdir, so we can link from the coverage
    # graph
    perf_mapping = self.PERF_TEST_MAPPINGS[self._target]
    perf_id = factory_properties.get('perf_id')
    perf_subdir = perf_mapping.get(perf_id)

    url = _GetArchiveUrl('coverage', perf_subdir)
    text = 'view coverage'
    cmd_archive = [self._python, self._archive_coverage,
           '--target', self._target,
           '--build-dir', self._build_dir,
           '--perf-subdir', perf_subdir]
    if factory_properties.get('use_build_number'):
      cmd_archive.extend(['--build-number', WithProperties("%(buildnumber)s")])

    self.AddArchiveStep(data_description='coverage', base_url=url,
                        link_text=text, command=cmd_archive)

  def AddSendTestParityStep(self, platform):
    cmd = [self._python,
           self._upload_parity_tool,
           self._build_dir,
           "http://chrome-test-parity.appspot.com/bulk_update",
           platform]
    self.AddTestStep(shell.ShellCommand, 'upload test parity', cmd)

  def AddDownloadAndExtractOfficialBuild(self, qa_identifier, branch=None):
    """Download and extract an official build.

    Assumes the zip file has e.g. "Google Chrome.app" in the top level
    directory of the zip file.
    """
    cmd = [self._python, self._download_and_extract_official_tool,
           '--identifier', qa_identifier,
           # TODO(jrg): for now we are triggered on a timer and always
           # use the latest build.  Instead we should trigger on the
           # presence of new build and pass that info down for a
           # --build N arg.
           '--latest']
    if branch:  # Fetch latest on given branch
      cmd += ['--branch', str(branch)]
    self.AddTestStep(commands.WaterfallLoggingShellCommand,
                     'Download and extract official build', cmd,
                     halt_on_failure=True)

  def AddGpuTests(self, factory_properties):
    """Runs gpu_tests binary and archives any results.

    This binary contains all the tests that should be run on the gpu bots.
    """
    self.AddBasicGTestTestStep('gpu_tests', factory_properties,
                               arg_list=['--use-gpu-in-tests'])

    # Setup environment for running gsutil, a Google Storage utility.
    gsutil = 'gsutil'
    if self._target_platform.startswith('win'):
      gsutil = 'gsutil.bat'
    env = {}
    env['GSUTIL'] = self.PathJoin(self._script_dir, gsutil)

    gpu_data = self.PathJoin('src', 'chrome', 'test', 'data', 'gpu')
    cmd = [self._python,
           self._gpu_archive_tool,
           '--run-id',
           WithProperties('%(got_revision)s'),
           '--generated-dir',
           self.PathJoin(gpu_data, 'generated'),
           '--gpu-reference-dir',
           self.PathJoin(gpu_data, 'gpu_reference'),
           '--sw-reference-dir',
           self.PathJoin(gpu_data, 'sw_reference')]
    self.AddTestStep(shell.ShellCommand, 'archive test results', cmd, env=env)

  def AddNaClIntegrationTestStep(self, factory_properties, target=None):
    target = target or self._target
    cmd = [self._python, self._nacl_integration_tester_tool,
           '--mode', target]
    self.AddTestStep(shell.ShellCommand, 'nacl_integration', cmd,
        do_step_if=self.TestStepFilter)

  def AddAnnotatedSteps(self, factory_properties, timeout=1200):
    factory_properties = factory_properties or {}
    cmd = [self._python, self._annotated_steps]
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='annotated_steps',
                          description='annotated_steps',
                          timeout=timeout,
                          haltOnFailure=True,
                          command=cmd)

  def _GetPyAutoCmd(self, src_base=None, script=None, factory_properties=None,
                    argv=None):
    """Get PyAuto Command line using arguments

    Args:
      src_base: relative path (from workdir) to src. Not needed if workdir is
                'build' (the default). Needed when workdir is not 'build' (like
                parent of 'build')
      script: script name that contain main function for test
      factory_properties: factory properties
      argv: argument list passed to the script

    Returns:
      a commandline list that can be executed
    """
    factory_properties = factory_properties or {}
    J = self.PathJoin
    pyauto_script = J('src', 'chrome', 'test', 'functional', 'media', script)
    # in case a '..' prefix is needed
    if src_base:
      pyauto_script = J(src_base, pyauto_script)

    pyauto_functional_cmd = ['python', pyauto_script] + argv
    if self._target_platform == 'win32':  # win needs python26
      py26 = J('src', 'third_party', 'python_26', 'python_slave.exe')
      if src_base:
        py26 = J(src_base, py26)
      pyauto_functional_cmd = ['cmd', '/C'] + [py26, pyauto_script, '-v']
    elif self._target_platform == 'darwin':
      pyauto_functional_cmd = ['python2.5', pyauto_script, '-v']
    elif (self._target_platform == 'linux2' and
          factory_properties.get('use_xvfb_on_linux')):
      # Run through runtest.py on linux to launch virtual X server.
      pyauto_functional_cmd = self.GetTestCommand('/usr/bin/python',
                                                  [pyauto_script] + argv)
      # Adjust runtest.py location.
      pyauto_functional_cmd[1] = os.path.join(os.path.pardir,
                                              pyauto_functional_cmd[1])
    return pyauto_functional_cmd

  def AddMediaPerfTests(self, timeout=1200, workdir=None, src_base=None,
                        factory_properties=None):
    """Add media performance tests.

    This method calls media_test_runner.py which runs media tests (including
    performance tests) with appropriate parameters (such as input data file
    name).
    """
    J = self.PathJoin
    dataset = J('src', 'chrome', 'test', 'data', 'media', 'csv',
                'media_list_data.csv')
    # in case a '..' prefix is needed.
    if src_base:
      dataset = J(src_base, dataset)
    # Adding appropriate parameters for perf script execution.
    argv = ['-i' + dataset]
    pyauto_functional_cmd = self._GetPyAutoCmd(
        src_base=src_base, script='media_test_runner.py', argv=argv,
        factory_properties=factory_properties)

    c = self.GetPerfStepClass(factory_properties, 'media_perf',
                              process_log.GraphingLogProcessor)

    self.AddTestStep(c, 'media_perf', pyauto_functional_cmd,
                     workdir=workdir, timeout=timeout)

def _GetArchiveUrl(archive_type, builder_name='%(build_name)s'):
  # The default builder name is dynamically filled in by
  # ArchiveCommand.createSummary.
  return '%s/%s/%s' % (config.Master.archive_url, archive_type, builder_name)
