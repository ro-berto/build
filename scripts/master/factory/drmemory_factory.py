# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
from buildbot.process import factory
from buildbot.process.properties import WithProperties
from buildbot.steps.source import SVN
from buildbot.steps.shell import Compile
from buildbot.steps.shell import Configure
from buildbot.steps.shell import ShellCommand
from buildbot.steps.shell import SetProperty
from buildbot.steps.shell import Test
from buildbot.steps.transfer import DirectoryUpload
from buildbot.steps.transfer import FileUpload
from buildbot.steps.transfer import FileDownload
from buildbot.status.builder import SUCCESS, WARNINGS, FAILURE

from master.factory import v8_factory

LATEST_WIN_BUILD = 'public_html/builds/drmemory-windows-latest-sfx.exe'

dr_svnurl = 'http://dynamorio.googlecode.com/svn/trunk'
drm_svnurl = 'http://drmemory.googlecode.com/svn/trunk'
bot_tools_svnurl = 'http://drmemory.googlecode.com/svn/buildbot/bot_tools'

# TODO(rnk): Don't make assumptions about absolute path layout.  This won't work
# on bare metal bots.  We can't use a relative path because we often configure
# builds at different directory depths.
WIN_BUILD_ENV_PATH = r'E:\b\build\scripts\slave\drmemory\build_env.bat'


def WindowsToOs(windows):
  """Takes a boolean windows value and returns a platform string.

  TODO(rnk): Switch to taking target_platform like all other factory code.
  """
  if windows:
    return 'windows'
  else:
    return 'linux'


class CTest(Test):

  """BuildStep that parses DR's runsuite output."""

  def __init__(self, os=None, **kwargs):
    assert os is not None
    self.__result = None
    PrepareBuildStepArgs(os, kwargs)
    Test.__init__(self, **kwargs)

  def createSummary(self, log):
    passed_count = 0
    failure_count = 0
    flaky_count = 0

    summary_lines = []
    found_summary = False
    # Don't use 'readlines' because we want both stdout and stderr.
    for line in log.getText().split('\n'):
      if line.strip() == 'RESULTS':
        assert not found_summary, 'Found two summaries!'
        found_summary = True
      if found_summary:
        summary_lines.append(line)
        # We try to recognize every line of the summary, because
        # if we fail to match the failure count line we might stay
        # green when we should be red.
        if line.strip() == 'RESULTS':
          continue  # Start of summary line
        if not line.strip():
          continue  # Blank line
        if re.match('^\t', line):
          continue  # Test failure lines start with tabs
        if 'build successful; no tests for this build' in line:
          continue  # Successful build with no tests
        if 'Error in read script' in line:
          continue  # DR i#636: Spurious line from ctest

        # All tests passed for this config.
        match = re.search('all (?P<passed>\d+) tests passed', line)
        if match:
          passed_count += int(match.group('passed'))
          continue

        # Some tests failed in this config.
        match = re.match(r'^[^:]*: (?P<passed>\d+) tests passed, '
                          '\*\*\*\* (?P<failed>\d+) tests failed'
                          '(, of which (?P<flaky>\d+) were flaky)?:',
                         line)
        if match:
          passed_count += int(match.group('passed'))
          failure_count += int(match.group('failed'))
          num_flaky_str = match.group('flaky')
          if num_flaky_str:
            flaky_count += int(num_flaky_str)
        else:
          # Add a fake failure so we get notified.  Put the warning
          # before the line we don't recognize.
          failure_count += 1
          summary_lines[-1:-1] = ['WARNING: next line unrecognized\n']

    if not found_summary:
      # Add a fake failure so we get notified.
      failure_count += 1
      summary_lines.append('WARNING: Failed to find summary in stdio.\n')

    self.setTestResults(passed=passed_count,
                        failed=failure_count - flaky_count,
                        warnings=flaky_count)

    if failure_count > 0:
      if failure_count > flaky_count:
        self.__result = FAILURE
      else:
        self.__result = WARNINGS
      summary_name = 'summary: %d failed' % failure_count
      if flaky_count > 0:
        summary_name += ', %d flaky failed' % flaky_count
      self.addCompleteLog(summary_name, ''.join(summary_lines))
    else:
      self.__result = SUCCESS

    got_revision = self.getProperty('got_revision')
    buildnumber  = self.getProperty('buildnumber')
    buildername  = self.getProperty('buildername')
    if 'drm' in buildername:
      self.addURL('test logs',
                  'http://build.chromium.org/p/client.drmemory/testlogs/' +
                  'from_%s/testlogs_r%s_b%s.7z' % \
                  (buildername, got_revision, buildnumber))

  def evaluateCommand(self, cmd):
    if self.__result is not None:
      return self.__result
    return Test.evaluateCommand(self, cmd)


class DrMemoryTest(Test):
  def __init__(self, **kwargs):
    self.failed__ = False  # there's a 'failed' method in Test, ouch!
    Test.__init__(self, **kwargs)

  def createSummary(self, log):
    failed_tests = []
    summary = []
    report_count = 0
    assert_failure = None

    # Don't use 'readlines' because we want both stdout and stderr.
    for line in log.getText().split('\n'):
      m = re.match('\[  FAILED  \] (.*\..*) \([0-9]+ ms\)', line.strip())
      if m:
        failed_tests.append(m.groups()[0])  # Append failed test name.

      DRM_PREFIX = '~~[Dr\.M0-9]+~~ '
      m = re.match(DRM_PREFIX + '(.*)', line)
      if m:
        summary.append(m.groups()[0])

      m = re.match(DRM_PREFIX + '*([0-9]+) unique,.*total,* (.*)', line)
      if m:
        (error_count, _) = m.groups()
        error_count = int(error_count)
        report_count += error_count

      m = re.match(DRM_PREFIX + 'ASSERT FAILURE \(.*\): (.*)', line)
      if m:
        assert_failure = 'ASSERT FAILURE: ' + m.groups()[0]

    if assert_failure:
      self.failed__ = True
      self.addCompleteLog('ASSERT FAILURE!!!', assert_failure)

    if failed_tests:
      self.failed__ = True
      self.setTestResults(failed=len(failed_tests))
      self.addCompleteLog('%d tests failed' % len(failed_tests),
                            '\n'.join(failed_tests))
    if report_count > 0:
      self.failed__ = True
      self.setTestResults(warnings=report_count)

    self.addCompleteLog('summary: %d report(s)' % report_count,
                        ''.join(summary))

  def evaluateCommand(self, cmd):
    if self.failed__:
      return FAILURE
    return Test.evaluateCommand(self, cmd)

def CreateAppTest(windows, app_name, app_cmd, build_mode, run_mode,
                  use_syms=True, **kwargs):
  # Pick exe from build mode.
  if windows:
    cmd = ['build_drmemory-%s-32\\bin\\drmemory' % build_mode]
  else:
    cmd = ['build_drmemory-%s-32/bin/drmemory.pl' % build_mode]
  # Default flags turn off message boxes, notepad, and print to stderr.
  cmd += ['-dr_ops', '-msgbox_mask 0 -stderr_mask 15',
          '-results_to_stderr', '-batch']
  if windows:
    # FIXME: The point of these app tests is to verify that we get no false
    # positives on well-behaved applications, so we should remove these
    # extra suppressions.  We're not using them on dev machines but we'll
    # leave them on the bots and for tsan tests for now.
    cmd += ['-suppress',
            '..\\drmemory\\tests\\app_suite\\default-suppressions.txt']
  # Full mode flags are default, light mode turns off uninits and leaks.
  if run_mode == 'light':
    cmd += ['-light']
  cmd.append('--')
  cmd += app_cmd
  # Set _NT_SYMBOL_PATH appropriately.
  syms_part = ''
  env = {}
  if not use_syms:
    syms_part = 'nosyms '
    if windows:
      env['_NT_SYMBOL_PATH'] = ''
  step_name = '%s %s %s%s' % (build_mode, run_mode, syms_part, app_name)
  return DrMemoryTest(command=cmd,
                      env=env,
                      name=step_name,
                      descriptionDone=step_name,
                      description='run ' + step_name,
                      **kwargs)


class V8DrFactory(v8_factory.V8Factory):

  """Subclass of V8Factory to build DR alongside V8 for the same arch."""

  @staticmethod
  def _ArchToBits(arch):
    """Takes a V8 architecture and returns its bitwidth for DR."""
    if not arch:  # Default to x64, we don't have any real ia32 bots.
      return 64
    elif arch == 'x64':
      return 64
    elif arch == 'ia32':
      return 32
    assert False, 'Unsupported architecture'

  def BuildFactory(self, target_arch=None, *args, **kwargs):
    f = super(V8DrFactory, self).BuildFactory(*args,
                                              target_arch=target_arch,
                                              **kwargs)
    # Add in a build of DR.
    f.addStep(SVN(svnurl=dr_svnurl,
                  workdir='dynamorio',
                  mode='update',
                  name='Checkout DynamoRIO'))
    cflags = '-m%s' % self._ArchToBits(target_arch)
    cmake_env = {'CFLAGS': cflags, 'CXXFLAGS': cflags}
    # We use release DR on the bots because debug is too slow.
    f.addStep(Configure(command=['cmake', '..', '-DDEBUG=OFF'],
                        workdir='dynamorio/build',
                        name='Configure release DynamoRIO',
                        env=cmake_env))
    f.addStep(Compile(command=['make', '-j5'],
                      workdir='dynamorio/build',
                      name='Compile release DynamoRIO'))
    return f

  def V8Factory(self, target_arch=None, *args, **kwargs):
    assert 'shell_flags' not in kwargs
    bits = self._ArchToBits(target_arch)
    drrun = '../../dynamorio/build/bin%d/drrun' % bits
    # TODO(rnk): V8 tests tend to do a lot of flushing, which trigger repeated
    # resets that slow things down.  Pass "-reset_at_pending 0" to alleviate
    # this once we can get quoted strings through V8's test scripts.
    kwargs['shell_flags'] = '%s @' % drrun
    return super(V8DrFactory, self).V8Factory(*args, target_arch=target_arch,
                                              **kwargs)


def CreateDRInDrMemoryFactory(nightly=False, os='', os_version=''):
  ret = factory.BuildFactory()

  # DR factory - we checkout Dr. Memory and *then* update drmemory/dynamorio,
  # otherwise Buildbot goes crazy about multiple revisions/ChangeSources.
  ret.addStep(
    SVN(
        svnurl=drm_svnurl,
        workdir='drmemory',
        mode='update',
        name='Checkout Dr. Memory'))
  ret.addStep(
    ShellCommand(
        command=['svn', 'up', '--force', '../drmemory/dynamorio'],
        name='Update DR to ToT',
        description='update DR'))
  ret.addStep(
    SetProperty(
        command=['svnversion', '../drmemory/dynamorio'],
        property='dr_revision',
        name='Get DR revision',
        descriptionDone='Get DR revision',
        description='DR revision'))
  AddDRSuite(ret, '../drmemory/dynamorio', nightly, os, os_version)
  if os == 'linux':
    ret.addStep(
        DirectoryUpload(
            slavesrc='install/docs/html',
            masterdest='public_html/dr_docs'))
  return ret


def AddToolsSteps(f, os):
  """Add steps to update and unpack drmemory's tools from svn."""
  if os.startswith('win'):
    f.addStep(SVN(svnurl=bot_tools_svnurl,
                  workdir='bot_tools',
                  alwaysUseLatest=True,
                  mode='update',
                  name='update tools'))
    f.addStep(ShellCommand(command=['unpack.bat'],
                           workdir='bot_tools',
                           name='unpack tools',
                           description='unpack tools'))


def PrepareBuildStepArgs(os, step_kwargs):
  """Modify build step arguments to run the command with our custom tools."""
  assert os is not None
  if os.startswith('win'):
    command = step_kwargs.get('command')
    env = step_kwargs.get('env')
    if isinstance(command, list):
      command = [WIN_BUILD_ENV_PATH] + command
    else:
      command = WIN_BUILD_ENV_PATH + ' ' + command
    if env:
      env = dict(env)  # Copy
    else:
      env = {}
    env['BOTTOOLS'] = WithProperties('%(workdir)s\\bot_tools')
    step_kwargs['command'] = command
    step_kwargs['env'] = env


def DrShellCommand(os=None, **kwargs):
  """Execute a ShellCommand using some of DR's custom bot tools."""
  assert os is not None
  PrepareBuildStepArgs(os, kwargs)
  return ShellCommand(**kwargs)


def AddDRSuite(f, dr_path, nightly, os, os_version):
  AddToolsSteps(f, os)
  if nightly:
    assert os
    assert os_version
    os_mapping = {'win' : 'Windows', 'linux' : 'Linux'}
    site_name = '%s.%s.BuildBot' % (os_mapping[os], os_version.capitalize())
    suite_args = 'nightly;long;site=%s' % site_name
    step_name = 'Run DR nightly suite'
    timeout = 20 * 60  # 20min w/o output.  10 is too short for Windows.
  else:
    suite_args = ''  # TODO(rnk): Use a recent cmake so we can switch to ninja.
    step_name = 'Build and test DR'
    timeout = 10 * 60  # 10min w/o output
  runsuite_cmd = '%s/suite/runsuite.cmake' % dr_path
  if suite_args:
    runsuite_cmd += ',' + suite_args
  cmd = ['ctest', '--timeout', '120', '-VV', '-S', runsuite_cmd]
  f.addStep(CTest(command=cmd,
                  os=os,
                  name=step_name,
                  descriptionDone=step_name,
                  timeout=timeout))


def CreateDRFactory(nightly=False, os='', os_version=''):
  """Create a factory to run the DR pre-commit suite.

  Same as the above, except we just do a plain DR checkout instead of
  DR-within-drmemory.  Used on the client.dynamorio waterfall.
  """
  ret = factory.BuildFactory()
  ret.addStep(SVN(svnurl=dr_svnurl,
                  workdir='dynamorio',
                  mode='update',
                  name='update DynamoRIO'))
  AddDRSuite(ret, '../dynamorio', nightly, os, os_version)
  if os == 'linux':
    ret.addStep(
        DirectoryUpload(
            slavesrc='install/docs/html',
            masterdest='public_html/dr_docs'))
  return ret


def CreateDrMFactory(windows):
  os = WindowsToOs(windows)
  ret = factory.BuildFactory()
  ret.addStep(
      SVN(svnurl=drm_svnurl,
          workdir='drmemory',
          mode='update',
          name='Checkout Dr. Memory'))
  ret.addStep(
      SetProperty(
          command=['svnversion', '../drmemory/dynamorio'],
          property='dr_revision',
          name='Get DR revision',
          descriptionDone='Get DR revision',
          description='DR revision'))
  AddToolsSteps(ret, os)
  cmd = ['ctest', '--timeout', '60', '-VV', '-S',
         WithProperties('../drmemory/tests/runsuite.cmake,' +
                        'drmemory_only;build=%(buildnumber)s')]
  ret.addStep(
      CTest(
          command=cmd,
          name='Dr. Memory ctest',
          descriptionDone='runsuite',
          os=os,
          flunkOnFailure=False, # failure doesn't mark the whole run as failure
          warnOnFailure=True,
          timeout=600))
  if windows:
    app_suite_cmd = ['build_drmemory-dbg-32\\tests\\app_suite_tests.exe']
  else:
    app_suite_cmd = ['build_drmemory-dbg-32/tests/app_suite_tests']
  # Run app_suite tests in (dbg, rel) in light mode.
  for build_mode in ('dbg', 'rel'):
    ret.addStep(CreateAppTest(windows, 'app_suite_tests', app_suite_cmd,
                              build_mode, 'light', use_syms=True))
    if windows:
      ret.addStep(CreateAppTest(windows, 'app_suite_tests', app_suite_cmd,
                                build_mode, 'light', use_syms=False))
  if windows:
    ret.addStep(
        ShellCommand(
            command=[
                'svn', 'checkout', '--force',
                'http://data-race-test.googlecode.com/svn/trunk/',
                '../tsan'],
            name='Checkout TSan tests',
            description='checkout tsan tests'))
    ret.addStep(
        DrShellCommand(
            command=['make', '-C', '../tsan/unittest'],
            # suppress cygwin 'MSDOS' warnings
            env={'CYGWIN': 'nodosfilewarning'},
            os=os,
            name='Build TSan tests',
            descriptionDone='build tsan tests',
            description='build tsan tests'))

    tsan_suite_cmd = [('..\\tsan\\unittest\\bin\\'
                       'racecheck_unittest-windows-x86-O0.exe'),
                      ('--gtest_filter="-PositiveTests.FreeVsRead'
                       ':NegativeTests.WaitForMultiple*"'),
                      '-147']

    # Run tsan tests in (dbg, rel) cross (full, light).
    for build_mode in ('dbg', 'rel'):
      for run_mode in ('full', 'light'):
        ret.addStep(CreateAppTest(windows, 'TSan tests', tsan_suite_cmd,
                                  build_mode, run_mode, use_syms=True))
    # Do one more run of TSan + app_suite without any pdb symbols to make
    # sure our default suppressions match.
    ret.addStep(CreateAppTest(windows, 'TSan tests', tsan_suite_cmd,
                              'dbg', 'full', use_syms=False))

    ret.addStep(
        ShellCommand(
            command=[
                'taskkill', '/T', '/F', '/IM', 'drmemory.exe', '||',
                 'echo', 'Dr. Memory is not running'],
            alwaysRun=True,
            name='Kill Dr. Memory processes',
            description='taskkill'))

  ret.addStep(
      ShellCommand(
          command=['del' if windows else 'rm', 'testlogs.7z'],
          haltOnFailure=False,
          flunkOnFailure=False,
          warnOnFailure=True,
          name='Prepare to pack test results',
          description='cleanup'))

  testlog_dirs = ['build_drmemory-dbg-32/logs',
                  'build_drmemory-dbg-32/Testing/Temporary',
                  'build_drmemory-rel-32/logs',
                  'build_drmemory-rel-32/Testing/Temporary']
  if windows:
    testlog_dirs += ['xmlresults']
  else:
    testlog_dirs += ['xml:results']
  ret.addStep(DrShellCommand(command=['7z', 'a', 'testlogs.7z'] + testlog_dirs,
                             haltOnFailure=True,
                             os=os,
                             name='Pack test results',
                             description='pack results'))

  ret.addStep(
     FileUpload(
          slavesrc='testlogs.7z',
          masterdest=WithProperties(
              'public_html/testlogs/' +
              'from_%(buildername)s/testlogs_r%(got_revision)s_b' +
              '%(buildnumber)s.7z'),
          name='Upload test logs to the master'))
  return ret


def CreateDrMPackageFactory(windows):
  os = WindowsToOs(windows)
  ret = factory.BuildFactory()
  ret.addStep(
      SVN(svnurl=drm_svnurl,
          mode='clobber',
          name='Checkout Dr. Memory'))
  AddToolsSteps(ret, os)
  # package.cmake will complain if this does not start with 'DrMemory-'
  package_name = 'DrMemory-package'
  # The default package name has the version and revision, so we override it
  # to something we can predict.
  cpack_arg = 'cpackappend=set(CPACK_PACKAGE_FILE_NAME "%s")' % package_name
  cmd = ['ctest', '-VV', '-S', 'package.cmake,build=42;' + cpack_arg]
  ret.addStep(DrShellCommand(command=cmd,
                             os=os,
                             name='Package Dr. Memory'))

  if windows:
    OUTPUT_DIR = ('build_drmemory-debug-32\\' +
                  '_CPack_Packages\\Windows\\ZIP\\' + package_name)
    RES_FILE = 'drmemory-windows-r%(got_revision)s-sfx.exe'
    PUB_FILE = RES_FILE

    ret.addStep(
        DrShellCommand(
            command=['7z', 'a', '-sfx', WithProperties(RES_FILE), '*'],
            workdir=WithProperties('build\\' + OUTPUT_DIR),
            haltOnFailure=True,
            os=os,
            name='Pack test results',
            description='pack results'))
    ret.addStep(
        FileUpload(
            slavesrc=WithProperties(OUTPUT_DIR + '/' + RES_FILE),
            masterdest=LATEST_WIN_BUILD,
            name='Upload as latest build'))
  else:
    OUTPUT_DIR = ('build_drmemory-debug-32/' +
                  '_CPack_Packages/Linux/TGZ')
    RES_FILE = package_name + '.tar.gz'
    PUB_FILE = 'drmemory-linux-r%(got_revision)s.tar.gz'

  ret.addStep(
      FileUpload(
          slavesrc=WithProperties(OUTPUT_DIR + '/' + RES_FILE),
          masterdest=WithProperties('public_html/builds/' +
                                    PUB_FILE),
          name='Upload binaries to the master'))
  return ret


def CreateWinStabFactory():
  ret = factory.BuildFactory()
  SFX_NAME = 'drm-sfx'  # TODO: add .exe when BB supports that, d'oh!
  ret.addStep(
      FileDownload(mastersrc=LATEST_WIN_BUILD,
                   slavedest=(SFX_NAME + '.exe'),
                   name='Download the latest build'))
  ret.addStep(
      ShellCommand(command=[SFX_NAME, '-ounpacked', '-y'],
                   haltOnFailure=True,
                   name='Unpack the build',
                   description='unpack the build'))

  # Find out the revision number using -version
  def get_revision(rc, stdout, stderr):
    m = re.search(r'version \d+\.\d+\.(\d+)', stdout)
    if m:
      return { 'got_revision': int(m.groups()[0]) }
    return { 'failed_to_parse': stdout }
  ret.addStep(
      SetProperty(
          command=['unpacked\\bin\\drmemory', '-version'],
          extract_fn=get_revision,
          name='Get the revision number',
          description='get revision',
          descriptionDone='get revision'))

  # VP8 tests
  ret.addStep(
      DrMemoryTest(command=[
                      'bash',
                      'E:\\vpx\\vp8-test-vectors\\run_tests.sh',
                      ('--exec=unpacked/bin/drmemory.exe -batch '
                       '-no_check_leaks -no_count_leaks '
                       '-no_check_uninitialized '
                       'e:/vpx/b/Win32/Debug/vpxdec.exe'),
                      'E:\\vpx\\vp8-test-vectors',
                   ],
                   env={'PATH': 'C:\\cygwin\\bin;%PATH%'},
                   name='VP8 tests',
                   descriptionDone='VP8 tests',
                   description='run vp8 tests'))

  # Chromium tests
  for test in ['googleurl', 'printing', 'media', 'sql', 'crypto', 'remoting',
               'ipc', 'base', 'net', 'unit']:
    ret.addStep(
        Test(command=[
                 'E:\\chromium\\src\\tools\\valgrind\\chrome_tests.bat',
                 '-t', test, '--tool', 'drmemory_light', '--keep_logs',
             ],
             env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
             name=('Chromium \'%s\' tests' % test),
             descriptionDone=('\'%s\' tests' % test),
             description=('run \'%s\' tests' % test)))

  def isWeeklyRun(step):
    # No hasProperty, so we have to test for a lookup exception.
    try:
      step.getProperty('is_weekly')
    except KeyError:
      return False
    return True

  ret.addStep(ShellCommand(command='shutdown -t 2 -r -f',
                           name='reboot',
                           description='reboot',
                           descriptionDone='reboot',
                           doStepIf=isWeeklyRun))

  return ret



def CreateLinuxChromeFactory():
  ret = factory.BuildFactory()
  ret.addStep(
      SVN(
          svnurl=dr_svnurl,
          workdir='dynamorio',
          mode='update',
          name='Checkout DynamoRIO'))

  # If we need to execute 32-bit children, we'll need a full exports package.
  ret.addStep(Configure(command=['cmake', '..', '-DDEBUG=OFF'],
                        workdir='dynamorio/build',
                        name='Configure release DynamoRIO'))
  ret.addStep(Compile(command=['make', '-j5'],
                      workdir='dynamorio/build',
                      name='Compile release DynamoRIO'))

  test = 'DRT'
  ret.addStep(
      Test(command=' '.join([
              'xvfb-run', '-a',
              './dynamorio/build/bin64/drrun',
              './chromium/src/out/Release/DumpRenderTree',
              'file:///home/chrome-bot/bb.html',
              '>drt_out',
              '&&',
              'md5sum', '-c', '/home/chrome-bot/bb.html.md5'
           ]),
           name=('Chromium \'%s\' tests' % test),
           workdir='.',
           descriptionDone=('\'%s\' tests' % test),
           description=('run \'%s\' tests' % test)))

  # Chromium tests
  for test in ['googleurl', 'printing', 'sql', 'crypto', 'remoting',
               'ipc', 'media', 'base', 'browser', 'net', 'unit']:
    if test in ('ipc', 'unit', 'browser'):
      binary = test + '_tests'
    else:
      binary = test + '_unittests'
    cmd = [
        'xvfb-run', '-a',
        './dynamorio/build/bin64/drrun',
        './chromium/src/out/Release/%s' % binary
        ]
    if test == 'browser':
      cmd += ['--gtest_filter=AutofillTest.BasicFormFill']
    elif test == 'net':
      cmd += ['--gtest_filter=-CertDatabaseNSSTest.ImportCACertHierarchy*']
    ret.addStep(
        Test(command=cmd,
             name=('Chromium \'%s\' tests' % test),
             workdir='.',
             descriptionDone=('\'%s\' tests' % test),
             description=('run \'%s\' tests' % test)))

  return ret
