#!/usr/bin/env python
# Copyright (c) 2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import imp
import optparse
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import time
import traceback
import unittest


class Unbuffered:
  # Wrapper class to flush() after every write(), so logs get
  # line-by-line output from the unittest harness.
  def __init__(self, fp):
    self.fp = fp
  def write(self, arg):
    self.fp.write(arg)
    self.fp.flush()
  def __getattr__(self, attr):
    return getattr(self.fp, attr)

sys.stdout = Unbuffered(sys.stdout)
sys.stderr = Unbuffered(sys.stderr)


def time_string(seconds):
  """
  Returns a float representing number of seconds as a HH:MM:SS.d string.
  """
  if seconds is None:
    return 'None'
  minutes = int(seconds / 60)
  hours = int(minutes / 60)
  return '%d:%02d:%04.1f' % (hours, minutes % 60, seconds % 60.0)


class CommandRunner:
  """
  Executor class for commands, including "commands" implemented by
  Python functions.
  """
  verbose = True
  active = True

  def __init__(self, dictionary={}):
    self.subst_dictionary(dictionary)

  def subst_dictionary(self, dictionary):
    self._subst_dictionary = dictionary

  def subst(self, string, dictionary=None):
    """
    Substitutes (via the format operator) the values in the specified
    dictionary into the specified command.

    The command can be an (action, string) tuple.  In all cases, we
    perform substitution on strings and don't worry if something isn't
    a string.  (It's probably a Python function to be executed.)
    """
    if dictionary is None:
      dictionary = self._subst_dictionary
    if dictionary:
      try:
        string = string % dictionary
      except TypeError:
        pass
    return string

  def display(self, command, stdout=None, stderr=None):
    if not self.verbose:
      return
    if type(command) == type(()):
      func = command[0]
      args = command[1:]
      s = '%s(%s)' % (func.__name__, ', '.join(map(repr, args)))
    if type(command) == type([]):
      # TODO:  quote arguments containing spaces
      # TODO:  handle meta characters?
      s = ' '.join(command)
    else:
      s = self.subst(command)
    if not s.endswith('\n'):
      s += '\n'
    sys.stdout.write(s)

  def execute(self, command, stdout=None, stderr=None):
    """
    Executes a single command.
    """
    if not self.active:
      return 0
    if type(command) == type(''):
      command = self.subst(command)
      cmdargs = shlex.split(command)
      if cmdargs[0] == 'cd':
         command = (os.chdir,) + tuple(cmdargs[1:])
    if type(command) == type(()):
      func = command[0]
      args = command[1:]
      return func(*args)
    else:
      if stdout is None:
        stdout = subprocess.PIPE
      if stderr is None:
        stderr = subprocess.STDOUT
      p = subprocess.Popen(command,
                           shell=(sys.platform == 'win32'),
                           stdout=stdout,
                           stderr=stderr)
      p.wait()
      if p.stdout:
        self.stdout = p.stdout.read()
      return p.returncode

  def run(self, command, display=None, stdout=None, stderr=None):
    """
    Runs a single command, displaying it first.
    """
    if display is None:
      display = command
    self.display(display)
    return self.execute(command, stdout, stderr)


class targetTextTestResult(unittest.TestResult):
  """
  TestResult subclass for targets.

  This reports status in a GTest-like format, including separating the
  output from tests for different targets (which are actually separate
  targetTestCase instances) into seprate-looking GTest "TestCase" output.
  """
  # TODO(sgk):  This should probably be refactored into a re-usable
  # GTestResult class that handles the GTest-format output,
  # and a separate targetTextTestResult subclass that handles
  # the adaptation to Chromium build targets.
  def __init__(self, stream):
    super(targetTextTestResult, self).__init__()
    self.stream = stream
    self.successes = []
  def startTest(self, test):
    super(targetTextTestResult, self).startTest(test)
    if test.isFirstForTarget():
      self.stream.write('\n')
      fmt = '[----------] %d tests from %s\n'
      self.stream.write(fmt % (test.target_tests, test.target_name))
    self.stream.write('[ RUN      ] %s\n' % test)
  def stopTest(self, test):
    super(targetTextTestResult, self).stopTest(test)
    if test.isLastForTarget():
      # TODO(sgk):  print the elapsed time for the entire target's tests.
      fmt = '[----------] %d tests from %s ()\n'
      self.stream.write(fmt % (test.target_tests, test.target_name))
  def addSuccess(self, test):
    super(targetTextTestResult, self).addSuccess(test)
    self.successes.append(test)
    time_fmt = 'RESULT %s: %s= %.1f seconds\n'
    sys.stdout.write(time_fmt % (test.target_name,
                                 test.getTestMethodName(),
                                 test.timeTaken()))
    fmt = '[       OK ] %s (%s seconds)\n'
    self.stream.write(fmt % (test, time_string(test.timeTaken())))
  def addError(self, test, err):
    super(targetTextTestResult, self).addError(test, err)
    self.stream.write(self._exc_info_to_string(err, test))
    fmt = '[  ERROR   ] %s (%s seconds)\n'
    self.stream.write(fmt % (test, time_string(test.timeTaken())))
  def addFailure(self, test, err):
    super(targetTextTestResult, self).addFailure(test, err)
    self.stream.write(self._exc_info_to_string(err, test))
    fmt = '[  FAILED  ] %s (%s seconds)\n'
    self.stream.write(fmt % (test, time_string(test.timeTaken())))
  def allExecutedTests(self):
    """
    Returns the number of tests that executed successfuly, and either
    passed or failed.  (ERROR tests indicate failure of test execution,
    due to system error or tripping over a code problem in the test
    infrastructure itself.)
    """
    return len(self.successes) + len(self.failures)
  def printSummary(self):
    if self.successes:
      self.stream.write('[  PASSED  ] %d tests.\n' % len(self.successes))
    self.printErrorList('[  FAILED  ]', self.failures)
    self.printErrorList('[  ERROR   ]', self.errors)
  def printErrorList(self, flavour, errors):
    if not errors:
      return
    fmt = '%s %d tests, listed below:\n'
    self.stream.write(fmt % (flavour, len(errors)))
    for test, err in errors:
      self.stream.write('%s %s\n' % (flavour, test))


class targetTextTestRunner:
  """
  """
  # TODO(sgk):  This should probably be refactored into a re-usable
  # GTestRunner class that handles the GTest-format summary,
  # and a separate targetTextTestRunner subclass that handles
  # the pieces that are specific to Chromium build targets.
  def __init__(self, number_of_targets, number_of_tests,
                     stream=sys.stderr, *args, **kw):
    self.stream = unittest._WritelnDecorator(stream)
    self.number_of_targets = number_of_targets
    self.number_of_tests = number_of_tests
  def _makeResult(self):
    return targetTextTestResult(self.stream)
  def run(self, test):
    result = self._makeResult()
    fmt = '[==========] Running %d tests from %d test cases.\n'
    self.stream.write(fmt % (self.number_of_tests, self.number_of_targets))
    test(result)
    self.stream.write('\n')
    fmt = '[==========] %d tests from %d test cases ran.  ()\n'
    self.stream.write(fmt % (result.allExecutedTests(), self.number_of_targets))
    result.printSummary()
    return result


class targetTestCase(unittest.TestCase):
  """
  Test case for testing builds of an individual target.

  Specific build tools (Visual Studio, XCode, SCons, Make) should
  create subclasses with their specific build commands,
  output directory, etc.

  This class notably takes care of invoking fixtures that should only
  be set up or torn down once for a given target, regardless of how many
  individual tests use the configuration.
  """
  def __init__(self, target_name, gyp_file, opts, target_tests,
                     target_set_ups, target_tear_downs, *args, **kw):
    super(targetTestCase, self).__init__(*args, **kw)
    self.gyp_file = gyp_file
    self.target_name = target_name
    self.opts = opts
    self.target_tests = target_tests
    self.target_set_ups = target_set_ups
    self.target_tear_downs = target_tear_downs
    self.status = 0

  def getTestMethodName(self):
    """
    Returns the test method name for this test case instance,
    abstracting the difference between different versions of the
    unittest module.
    """
    try:
      return self._testMethodName
    except AttributeError:
      # Pre-2.5 unittest.py module.
      return self._TestCase__testMethodName

  def __str__(self):
    return self.target_name + '.' + self.getTestMethodName()

  def isFirstForTarget(self):
    return not self.target_set_ups.has_key(self.target_name)

  def isLastForTarget(self):
    return self.target_tear_downs[self.target_name] <= 0

  def rmtree(self, directory):
    if os.path.exists(directory):
      if self.opts.verbose:
        sys.stdout.write('rm -rf %s\n' % directory)
      if not self.opts.no_exec:
        shutil.rmtree(directory)

  def rename(self, source, destination):
    if os.path.exists(source):
      if self.opts.verbose:
        sys.stdout.write('mv %s %s\n' % (source, destination))
      if not self.opts.no_exec:
        os.rename(source, destination)

  def makedirs(self, directory, mode):
    if not os.path.exists(directory):
      if self.opts.verbose:
        sys.stdout.write('mkdir -p --mode=%o %s\n' % (mode, directory))
      if not self.opts.no_exec:
        os.makedirs(directory, mode)

  def setUp(self):
    if self.isFirstForTarget():
      self.target_set_ups[self.target_name] = 1
      self.target_tear_downs[self.target_name] = self.target_tests
      self.setUpOncePerTarget()
    else:
      self.target_set_ups[self.target_name] += 1

  def tearDown(self):
    self.target_tear_downs[self.target_name] -= 1
    if self.isLastForTarget():
      self.tearDownOncePerTarget()

  def setUpOncePerTarget(self):
    """
    Removes any existing output build directory (sconsbuild), and the
    target-specific output directory to which we'll move the build
    (sconsbuild.base, for example).   Makes a fresh output build
    directory.
    """
    self.rmtree(self.build_dir)
    self.rmtree(self.target_build_dir)
    self.makedirs(os.path.dirname(self.target_build_dir), 0755)
    self.makedirs(self.build_dir, 0755)

  def tearDownOncePerTarget(self):
    """
    Removes the output build directory.

    NOTE:  You probably want to override this in the tool-specific
    subclass.  Always blowing away the build_dir like this is the
    lowest-common-denominator approach to making sure we can continue on
    to the next case even if the disk fills up.  It may blow away logs
    or other things that you *do* want to keep for post-mortem debugging.
    """
    self.rmtree(self.build_dir)

  def _run_build_command(self, output_file):
    """
    Runs a single build command, capturing output in the specified file.
    """
    if self.opts.no_exec:
      output = None
    else:
      output = open(output_file, 'w')
    c = CommandRunner()
    self.startTime = time.time()
    try:
      run_status = c.run(self.build_cmd, stdout=output)
    finally:
      self.endTime = time.time()

    if run_status != 0:
      # TODO(sgk):  this should print the command line so they can
      # see what command caused the error even if -v isn't being used.
      #if not self.opts.verbose:
      #  sys.stdout.write('TODO\n')
      if not self.opts.no_exec:
        sys.stdout.write(open(output_file, 'r').read())

    if self.status == 0 and run_status:
      self.status = run_status

    self.failIf(run_status != 0, 'Non-zero exit status %r.' % run_status)

  def timeTaken(self):
    """
    Returns elapsed time spent executing this test case.
    """
    try:
      return (self.endTime - self.startTime)
    except AttributeError:
      return None


class msvsTestCase(targetTestCase):
  """
  Test case for verifying that full builds of a target with Visual
  Studio succeed (exits zero) and that a null rebuild immediately
  afterwards reports that the target is, in fact, up-to-date.
  """
  build_dir = 'src\\chrome\\Release'
  compile_py = '..\\..\\..\\scripts\\slave\\compile.py'

  def __init__(self, *args, **kw):
    super(msvsTestCase, self).__init__(*args, **kw)
    self.target_dir = 'src\\msvsbuild.%s' % self.target_name
    self.target_build_dir = self.target_dir + '\\Release'
    self.build_cmd = [
      sys.executable,
      self.compile_py,
      '--build-dir=src\\chrome',
      '--project=%s' % self.target_name,
    ]

  def tearDownOncePerTarget(self):
    """
    If the build succeeded, removes the output build directory
    (chrome\Release).  If the build failed, move the output build
    directory to the target-specific output directory (msvsbuild\Release).
    The logs were already written to the target-specific output directory.
    """
    if self.status == 0:
      self.rmtree(self.build_dir)
    else:
      self.rename(self.build_dir, self.target_build_dir)

  def full(self):
    """
    Perform a full build (implicitly, in a fresh build directory).
    """
    output_file = os.path.join(self.target_dir, 'Release-0-full.log')
    self._run_build_command(output_file)

  def null(self):
    """
    Perform a null (everything up-to-date) rebuild (implicitly, in a build
    directory just populated with a fresh build).  Verifies that the
    build was up-to-date by looking for the appropriate SCons message.
    """
    output_file = os.path.join(self.target_dir, 'Release-1-null.log')
    self._run_build_command(output_file)

    if not self.opts.no_exec:
      u = r'=== Build: \d+ succeeded, 0 failed, (\d+) up-to-date, 0 skipped ==='
      up_to_date = re.compile(u, re.M)
      output = open(output_file, 'r').read()
      m = up_to_date.search(output)
      if not m or m.group(1) == '0':
        if not self.opts.verbose:
          CommandRunner().display(self.build_cmd)
        if not m:
          sys.stdout.write('Failed to match the following in build output:\n')
          sys.stdout.write('    %s\n' % repr(u))
        else:
          sys.stdout.write('Reported 0 up-to-date in the build output:\n')
        sys.stdout.write(output)
        sys.stdout.write('\n')
        self.fail('Build not up to date')


class sconsTestCase(targetTestCase):
  """
  Test case for verifying that full builds of a target with SCons succeed
  (exit zero) and that a null rebuild immediately afterwards reports
  that the target is, in fact, up-to-date.
  """
  build_dir = 'src/sconsbuild'
  compile_py = '../../../scripts/slave/compile.py'
  full_log_name = 'Release-0-full.log'
  null_log_name = 'Release-1-null.log'

  def __init__(self, *args, **kw):
    super(sconsTestCase, self).__init__(*args, **kw)
    self.target_build_dir = "%s.%s" % (self.build_dir, self.target_name)
    self.build_cmd = [
      sys.executable,
      self.compile_py,
      '--build-dir=src/build',
      self.target_name
    ]

  def tearDownOncePerTarget(self):
    """
    If the build succeeded, remove the entire build directory after
    saving the logs.  If the build failed, save the build directory.
    """
    if self.status == 0:
      self.makedirs(self.target_build_dir, 0755)
      self.rename(os.path.join(self.build_dir, self.full_log_name),
                  os.path.join(self.target_build_dir, self.full_log_name))
      self.rename(os.path.join(self.build_dir, self.null_log_name),
                  os.path.join(self.target_build_dir, self.null_log_name))
      self.rmtree(self.build_dir)
    else:
      self.rename(self.build_dir, self.target_build_dir)

  def full(self):
    """
    Perform a full build (implicitly, in a fresh build directory).
    """
    output_file = os.path.join(self.build_dir, self.full_log_name)
    self._run_build_command(output_file)

  def null(self):
    """
    Perform a null (everything up-to-date) rebuild (implicitly, in a build
    directory just populated with a fresh build).  Verifies that the
    build was up-to-date by looking for the appropriate SCons message.
    """
    output_file = os.path.join(self.build_dir, self.null_log_name)
    self._run_build_command(output_file)

    if not self.opts.no_exec:
      up_to_date = "scons: `%s' is up to date." % self.target_name
      nothing_to_be_done = "scons: Nothing to be done for `%s'." % self.target_name
      output = open(output_file, 'r').read()
      if (not up_to_date in output and not nothing_to_be_done in output):
        if not self.opts.verbose:
          CommandRunner().display(self.build_cmd)
        msg = 'Failed to find either of the following in build output:\n'
        sys.stdout.write(msg)
        sys.stdout.write('    %r\n' % up_to_date)
        sys.stdout.write('    %r\n' % nothing_to_be_done)
        sys.stdout.write(output)
        sys.stdout.write('\n')
        self.fail('Build not up to date')


class xcodeTestCase(targetTestCase):
  """
  Test case for verifying that full builds of a target with XCode
  succeed (exits zero) and that a null rebuild immediately
  afterwards reports that the target is, in fact, up-to-date.
  """
  build_dir = 'src/xcodebuild'
  compile_py = os.path.abspath('../../../scripts/slave/compile.py')
  full_log_name = 'Release-0-full.log'
  null_log_name = 'Release-1-null.log'

  def __init__(self, *args, **kw):
    super(xcodeTestCase, self).__init__(*args, **kw)
    self.build_dir = os.path.abspath(self.build_dir)
    self.target_build_dir = "%s.%s" % (self.build_dir, self.target_name)
    self.xcodeproj = self.gyp_file.replace('.gyp', '.xcodeproj')
    self.build_cmd = [
      sys.executable,
      self.compile_py,
      '--build-dir=' + os.path.dirname(self.xcodeproj),
      '--',
      '-project', os.path.split(self.xcodeproj)[1],
      '-target', self.target_name,
    ]

  def tearDownOncePerTarget(self):
    """
    If the build succeeded, remove the entire build directory after
    saving the logs.  If the build failed, save the build directory.
    """
    if self.status == 0:
      self.makedirs(self.target_build_dir, 0755)
      self.rename(os.path.join(self.build_dir, self.full_log_name),
                  os.path.join(self.target_build_dir, self.full_log_name))
      self.rename(os.path.join(self.build_dir, self.null_log_name),
                  os.path.join(self.target_build_dir, self.null_log_name))
      self.rmtree(self.build_dir)
    else:
      self.rename(self.build_dir, self.target_build_dir)

  def full(self):
    """
    Perform a full build (implicitly, in a fresh build directory).
    """
    output_file = os.path.join(self.build_dir, self.full_log_name)
    self._run_build_command(output_file)

  phase_script_execution = ("\n"
                            "PhaseScriptExecution /\\S+/Script-[0-9A-F]+\\.sh\n"
                            "    cd /\\S+\n"
                            "    /bin/sh -c /\\S+/Script-[0-9A-F]+\\.sh\n"
                            "(make: Nothing to be done for `all'\\.\n)?")
  phase_script_execution_re = re.compile(phase_script_execution,
                                         re.S)

  def null(self):
    """
    Perform a null (everything up-to-date) rebuild (implicitly, in a build
    directory just populated with a fresh build).  Verifies that the
    build was up-to-date by looking for the appropriate SCons message.
    """
    output_file = os.path.join(self.build_dir, self.null_log_name)
    self._run_build_command(output_file)

    if not self.opts.no_exec:
      check = "Checking Dependencies...\n** BUILD SUCCEEDED **\n"
      output = open(output_file, 'r').read()
      output = self.phase_script_execution_re.sub('', output)
      if not output.endswith(check):
        if not self.opts.verbose:
          CommandRunner().display(self.build_cmd)
        sys.stdout.write('Build output did not end with the following:\n')
        sys.stdout.write('    %r\n' % check)
        sys.stdout.write('Build output:\n')
        sys.stdout.write(output)
        sys.stdout.write('\n')
        self.fail('Build not up to date')


def run_tests(test_case_class, opts, target_names, gyp_files):
  """
  Runs tests for the specified target_names.
  """
  test_method_names = ['full', 'null']
  target_set_ups = {}
  target_tear_downs = {}
  suite = unittest.TestSuite()
  for target in target_names:
    suite.addTests([test_case_class(target,
                                    gyp_files[target],
                                    opts,
                                    len(test_method_names),
                                    target_set_ups,
                                    target_tear_downs,
                                    name)
                    for name in test_method_names])
  runner = targetTextTestRunner(len(target_names),
                                suite.countTestCases(),
                                stream=sys.stdout)
  if runner.run(suite).wasSuccessful():
    return 0
  else:
    return 1


# A hard-coded list of the targets with "fast" full builds (< 20 seconds
# on reasonably fast Linux and Windows system as of July 2009) which can
# be used readily for development and debugging work on this script.

fast_targets = [
  'app_resources',
  'app_strings',
  'base_gfx',
  'bzip2',
  'chrome_resources',
  'codesighs',
  'config',
  'default_extensions',
  'ffmpeg',
  'ffmpeg_binaries',
  'gmock',
  'gmockmain',
  'googleurl',
  'gtest',
  'gtestmain',
  'hunspell',
  'icudata',
  'inspector_resources',
  'js2c',
  'libjpeg',
  'libpng',
  'libxslt',
  'lzma_sdk',
  'maptsvdifftool',
  'modp_b64',
  'net_resources',
  'net_test_support',
  'npapi',
  'pcre',
  'printing',
  'sdch',
  'support',
  'test_support_base',
  'theme_resources',
  'utility',
  'v8_nosnapshot',
  'webkit_resources',
  'webkit_strings',
  'worker',
  'wtf',
  'zlib',
]


# Targets that we don't care about test building.
#
# TODO:  the "explicitly runs every time" targets should be run
# for timing, and we just shouldn't worry about the null build.

exclude_targets = [
  'app_id', # explicitly runs every time
  'cygwin', # explicitly runs every time
  'lastchange', # explicitly runs every time
  'pull_in_all',
  'pull_in_test_shell',
]


def manual_import(filename):
  """
  Imports the specified Python source filename manually, even if it
  doesn't have a .py suffix.  Clean up the compiled module file after.
  """
  module_name = os.path.basename(filename)
  result = imp.load_module(module_name,
                           open(filename),
                           filename,
                           ('', 'U', imp.PY_SOURCE))
  try:
    os.unlink(filename + 'c')
  except EnvironmentError:
    pass
  return result


def get_all_gyp_targets(filename, format):
  """
  Returns a dict mapping all GYP target names (from loading the specified
  gyp filename) to their .gyp file.
  """
  # TODO(sgk):  this assumes we're in the build directory above src/;
  # either find gyp relative to this script, or use a copy that
  # gets checked in with depot_tools.
  sys.path.append(os.path.join(os.getcwd(), 'src/tools/gyp/pylib'))
  import gyp
  from gyp.common import ParseQualifiedTarget

  gyp_chromium = manual_import('src/build/gyp_chromium')
  includes = gyp_chromium.additional_include_files()

  [generator, flat_list, targets, data] = gyp.Load(filename, format,
                                                   includes=includes,
                                                   depth='src')
  result = {}
  for qualified_target in flat_list:
    gyp_file, target_name, toolset = ParseQualifiedTarget(qualified_target)
    result[target_name] = gyp_file
  return result

def main(argv=None):
  if argv is None:
    argv = sys.argv

  parser = optparse.OptionParser(usage="target-tests.py [-hnv] [-f FILE]")
  parser.add_option("--fast-targets", action="store", metavar="NUM",
            help="Build only NUM 'fast' targets (for script debugging)")
  parser.add_option("-f", "--file", action="store",
            help="Read targets from the specified .gyp file")
  parser.add_option("-n", "--no-exec", action="store_true",
            help="no execute, just print the command line")
  parser.add_option("-v", "--verbose", action="store_true",
            help="verbose, print command lines")
  opts, args = parser.parse_args(argv[1:])

  CommandRunner.verbose = opts.verbose
  CommandRunner.active = not opts.no_exec

  if opts.file:
    gyp_file = opts.file
  else:
    if sys.platform == 'win32':
      # Windows build still uses chrome as its entry point.
      gyp_file = ['src/chrome/chrome.gyp']
    else:
      gyp_file = ['src/build/all.gyp']

  if sys.platform == 'win32':
    gyp_format = 'msvs'
    test_case_class = msvsTestCase
  elif sys.platform == 'darwin':
    gyp_format = 'xcode'
    test_case_class = xcodeTestCase
  else:
    gyp_format = 'scons'
    test_case_class = sconsTestCase

  all_gyp_targets = get_all_gyp_targets(gyp_file, gyp_format)

  for target in exclude_targets:
    try:
      del all_gyp_targets[target]
    except KeyError:
      pass

  if not args:
    if opts.fast_targets == 'all':
      args = fast_targets
    elif opts.fast_targets:
      args = random.sample(fast_targets, int(opts.fast_targets))
    else:
      args = sorted(all_gyp_targets.keys())

  return run_tests(test_case_class, opts, args, all_gyp_targets)


if __name__ == "__main__":
  sys.exit(main())
