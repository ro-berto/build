#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run a chrome test executable, used by the buildbot slaves.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import copy
import logging
import optparse
import os
import re
import sys

# sys.path needs to be modified here because python2.6 automatically adds the
# system "google" module (/usr/lib/pymodules/python2.6/google) to sys.modules
# when we import "chromium_config" (I don't know why it does this). This causes
# the import of our local "google.*" modules to fail because python seems to
# only look for a system "google.*", even if our path is in sys.path before
# importing "google.*". If we modify sys.path here, before importing
# "chromium_config", python2.6 properly uses our path to find our "google.*"
# (even though it still automatically adds the system "google" module to
# sys.modules, and probably should still be using that to resolve "google.*",
# which I really don't understand).
sys.path.insert(0, os.path.abspath('src/tools/python'))

# Because of this dependency on a chromium checkout, we need to disable some
# pylint checks.
# pylint: disable=E0611
# pylint: disable=E1101
from common import chromium_utils
from slave import slave_utils
import config

# pylint: disable=F0401
import google.httpd_utils
import google.platform_utils


USAGE = '%s [options] test.exe [test args]' % os.path.basename(sys.argv[0])


class GTestUnexpectedDeathTracker(object):
  """A lightweight version of log parser that keeps track of running tests
  for unexpected timeout or crash."""

  def __init__(self):
    self._current_test = None
    self._test_start   = re.compile('\[\s+RUN\s+\] (\w+\.\w+)')
    self._test_ok      = re.compile('\[\s+OK\s+\] (\w+\.\w+)')
    self._test_fail    = re.compile('\[\s+FAILED\s+\] (\w+\.\w+)')

    self.failed_tests = set()

  def OnReceiveLine(self, line):
    results = self._test_start.search(line)
    if results:
      self._current_test = results.group(1)
      return

    results = self._test_ok.search(line)
    if results:
      self._current_test = ''
      return

    results = self._test_fail.search(line)
    if results:
      self.failed_tests.add(results.group(1))
      self._current_test = ''
      return

  def GenerateXML(self, path):
    """Generates a minimal XML file that includes failed tests that may
    have crashed or hung for an unexpected reason.  Returns False if no
    current test has been recorded or if it fails to open a file.
    """
    if not self._current_test:
      return False
    self.failed_tests.add(self._current_test)

    if not os.path.exists(os.path.dirname(path)):
      os.makedirs(os.path.dirname(path))
    fout = open(path, "w")
    if not fout:
      return False
    try:
      fout.write('<?xml version="1.0" encoding="UTF-8"?>\n')
      fout.write('<testsuites name="AllTests">\n')

      last_test_suite = None
      for test in sorted(self.failed_tests):
        test_name = test.split('.')
        if len(test_name) != 2:
          continue
        if last_test_suite != test_name[0]:
          if last_test_suite:
            fout.write('</testsuite>\n')
          fout.write('<testsuite name="%s">\n' % test_name[0])
          last_test_suite = test_name[0]

        fout.write('<testcase name="%s" status="run" time="0" classname="%s">'
                  % (test_name[1], test_name[0]))
        fout.write('<failure message="" type=""></failure>')
        fout.write('</testcase>\n')

      if last_test_suite:
        fout.write('</testsuite>\n')
      fout.write('</testsuites>\n')
    finally:
      fout.close()
    return True


def _RunGTestCommand(command, results_tracker):
  if results_tracker:
    return chromium_utils.RunCommand(
        command, parser_func=results_tracker.OnReceiveLine)
  else:
    return chromium_utils.RunCommand(command)


def _GenerateJSONForTestResults(options, results_tracker):
  """Generate (update) a JSON file from the gtest results XML and
  upload the file to the archive server.
  The archived JSON file will be placed at:
  www-dir/gtest_results/buildname/testname/results.json
  on the archive server.
  Note that it adds slave's webkit/tools/layout_tests to the PYTHONPATH
  to run the JSON generator.

  Args:
    options: command-line options that are supposed to have build_dir,
        results_directory, builder_name, build_name and test_output_xml values.
  """
  if not os.path.exists(options.test_output_xml):
    # The file did not get generated. Try if we can generate a XML file
    # from the log output.
    try:
      results_tracker.GenerateXML(options.test_output_xml)
    except (OSError, IOError), e:
      print 'Unexpected error while generating XML: ', e
      return
    if not os.path.exists(options.test_output_xml):
      print 'ERROR: %s not get generated.' % options.test_output_xml
      return

  build_dir = os.path.abspath(options.build_dir)
  slave_name = slave_utils.SlaveBuildName(build_dir)
  postproc_options = copy.copy(options)
  postproc_options.build_name = slave_name
  postproc_options.input_results_xml = options.test_output_xml
  postproc_options.builder_base_url = '%s/gtest_results/%s/%s' % (
      config.Master.archive_url, slave_name, options.test_type)

  try:
    sys.path.append(chromium_utils.FindUpward(
        build_dir, 'webkit', 'tools', 'layout_tests', 'webkitpy',
        'layout_tests'))
    import test_output_xml_to_json
    test_output_xml_to_json.JSONGeneratorFromXML(postproc_options)

    dest_dir = os.path.join(config.Archive.gtest_result_archive,
        slave_name)
    dest_dir = os.path.join(dest_dir, options.test_type)
    src_full_path = os.path.join(options.results_directory, 'results.json')

    print 'copying dashboard file %s to %s' % (src_full_path, dest_dir)
    chromium_utils.MaybeMakeDirectoryOnArchiveHost(dest_dir)
    chromium_utils.CopyFileToArchiveHost(src_full_path, dest_dir)
  except (OSError, IOError), e:
    print 'Unexpected error while generating JSON: ', e

def main_mac(options, args):
  if len(args) < 1:
    raise chromium_utils.MissingArgument('Usage: %s' % USAGE)

  test_exe = args[0]
  build_dir = os.path.normpath(os.path.abspath(options.build_dir))
  test_exe_path = os.path.join(build_dir, options.target, test_exe)
  if not os.path.exists(test_exe_path):
    pre = 'Unable to find %s\n' % test_exe_path
    build_dir = os.path.join(os.path.dirname(build_dir), 'xcodebuild')
    test_exe_path = os.path.join(build_dir, options.target, test_exe)
    if not os.path.exists(test_exe_path):
      msg = pre + 'Unable to find %s' % test_exe_path
      raise chromium_utils.PathNotFound(msg)

  http_server = None
  if options.document_root:
    platform_util = google.platform_utils.PlatformUtility(build_dir)

    # Name the output directory for the exe, without its path or suffix.
    # e.g., chrome-release/httpd_logs/unit_tests/
    test_exe_name = os.path.splitext(os.path.basename(test_exe_path))[0]
    output_dir = os.path.join(slave_utils.SlaveBaseDir(build_dir),
                              'httpd_logs',
                              test_exe_name)

    apache_config_dir = google.httpd_utils.ApacheConfigDir(build_dir)
    httpd_conf_path = os.path.join(apache_config_dir, 'httpd2_mac.conf')
    mime_types_path = os.path.join(apache_config_dir, 'mime.types')
    document_root = os.path.abspath(options.document_root)

    start_cmd = platform_util.GetStartHttpdCommand(output_dir,
                                                   httpd_conf_path,
                                                   mime_types_path,
                                                   document_root)
    stop_cmd = platform_util.GetStopHttpdCommand()
    http_server = google.httpd_utils.ApacheHttpd(start_cmd, stop_cmd, [8000])
    try:
      http_server.StartServer()
    except google.httpd_utils.HttpdNotStarted, e:
      raise google.httpd_utils.HttpdNotStarted('%s. See log file in %s' %
                                               (e, output_dir))

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  chromium_utils.RemoveChromeTemporaryFiles()

  if options.run_shell_script:
    command = ['sh', test_exe_path]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  results_tracker = None
  if options.generate_json_file:
    results_tracker = GTestUnexpectedDeathTracker()

    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  result = _RunGTestCommand(command, results_tracker)

  if options.document_root:
    http_server.StopServer()

  if options.generate_json_file:
    _GenerateJSONForTestResults(options, results_tracker)

  return result

def main_linux(options, args):
  if len(args) < 1:
    raise chromium_utils.MissingArgument('Usage: %s' % USAGE)

  build_dir = os.path.normpath(os.path.abspath(options.build_dir))
  slave_name = slave_utils.SlaveBuildName(build_dir)
  # If this is a sub-project build (i.e. there's a 'sconsbuild' in build_dir),
  # look for the test binaries there, otherwise look for the top-level build
  # output.
  # This assumes we never pass a build_dir which might contain build output that
  # we're not trying to test. This is currently a safe assumption since we don't
  # have any builders that do both sub-project and top-level builds (only
  # Modules builders do sub-project builds), so they shouldn't ever have both
  # 'build_dir/sconsbuild' and 'build_dir/../sconsbuild'.
  outdir = None
  if os.path.exists(os.path.join(build_dir, 'sconsbuild')):
    outdir = 'sconsbuild'
  elif os.path.exists(os.path.join(build_dir, 'out')):
    outdir = 'out'

  if outdir:
    bin_dir = os.path.join(build_dir, outdir, options.target)
    src_dir = os.path.join(slave_utils.SlaveBaseDir(build_dir), 'build', 'src')
    os.environ['CR_SOURCE_ROOT'] = src_dir
  else:
    if os.path.exists(os.path.join(build_dir, '..', 'sconsbuild')):
      bin_dir = os.path.join(build_dir, '..', 'sconsbuild', options.target)
    else:
      bin_dir = os.path.join(build_dir, '..', 'out', options.target)

  slave_utils.StartVirtualX(slave_name, bin_dir)

  test_exe = args[0]
  test_exe_path = os.path.join(bin_dir, test_exe)
  if not os.path.exists(test_exe_path):
    msg = 'Unable to find %s' % test_exe_path
    raise chromium_utils.PathNotFound(msg)

  # Don't use a sandbox when running tests. Ideally we _would_ use a sandbox,
  # but since the sandbox needs to be suid and owned by root, the one from the
  # current build won't work (the buildbot would need sudo to set the proper
  # file attributes), and we'd rather have no sandbox than pull in an old
  # (possibly incompatible) one from the system.
  os.environ['CHROME_DEVEL_SANDBOX'] = ''

  http_server = None
  if options.document_root:
    platform_util = google.platform_utils.PlatformUtility(build_dir)

    # Name the output directory for the exe, without its path or suffix.
    # e.g., chrome-release/httpd_logs/unit_tests/
    test_exe_name = os.path.splitext(os.path.basename(test_exe_path))[0]
    output_dir = os.path.join(slave_utils.SlaveBaseDir(build_dir),
                              'httpd_logs',
                              test_exe_name)

    # Sanity checks for httpd2_linux.conf.
    for ssl_file in 'ssl.conf', 'ssl.load':
      ssl_path = os.path.join('/etc/apache/mods-enabled', ssl_file)
      if not os.path.exists(ssl_path):
        sys.stderr.write('WARNING: %s missing, http server may not start\n' %
                         ssl_path)
    if not os.access('/var/run/apache2', os.W_OK):
      sys.stderr.write('WARNING: cannot write to /var/run/apache2, '
                       'http server may not start\n')

    apache_config_dir = google.httpd_utils.ApacheConfigDir(build_dir)
    httpd_conf_path = os.path.join(apache_config_dir, 'httpd2_linux.conf')
    mime_types_path = os.path.join(apache_config_dir, 'mime.types')
    document_root = os.path.abspath(options.document_root)

    start_cmd = platform_util.GetStartHttpdCommand(output_dir,
                                                   httpd_conf_path,
                                                   mime_types_path,
                                                   document_root)
    stop_cmd = platform_util.GetStopHttpdCommand()
    http_server = google.httpd_utils.ApacheHttpd(start_cmd, stop_cmd, [8000])
    try:
      http_server.StartServer()
    except google.httpd_utils.HttpdNotStarted, e:
      raise google.httpd_utils.HttpdNotStarted('%s. See log file in %s' %
                                               (e, output_dir))

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  chromium_utils.RemoveChromeTemporaryFiles()

  os.environ['LD_LIBRARY_PATH'] = '%s:%s/lib:%s/lib.target' % (bin_dir, bin_dir,
                                                               bin_dir)
  if options.run_shell_script:
    command = ['sh', test_exe_path]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  results_tracker = None
  if options.generate_json_file:
    results_tracker = GTestUnexpectedDeathTracker()

    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  result = _RunGTestCommand(command, results_tracker)

  if options.document_root:
    http_server.StopServer()

  slave_utils.StopVirtualX(slave_name)

  if options.generate_json_file:
    _GenerateJSONForTestResults(options, results_tracker)

  return result

def main_win(options, args):
  """Using the target build configuration, run the executable given in the
  first non-option argument, passing any following arguments to that
  executable.
  """
  if len(args) < 1:
    raise chromium_utils.MissingArgument('Usage: %s' % USAGE)

  test_exe = args[0]
  build_dir = os.path.abspath(options.build_dir)
  test_exe_path = os.path.join(build_dir, options.target, test_exe)
  if not os.path.exists(test_exe_path):
    raise chromium_utils.PathNotFound('Unable to find %s' % test_exe_path)

  http_server = None
  if options.document_root:
    platform_util = google.platform_utils.PlatformUtility(build_dir)

    # Name the output directory for the exe, without its path or suffix.
    # e.g., chrome-release/httpd_logs/unit_tests/
    test_exe_name = os.path.basename(test_exe_path).rsplit('.', 1)[0]
    output_dir = os.path.join(slave_utils.SlaveBaseDir(build_dir),
                              'httpd_logs',
                              test_exe_name)

    apache_config_dir = google.httpd_utils.ApacheConfigDir(build_dir)
    httpd_conf_path = os.path.join(apache_config_dir, 'httpd.conf')
    mime_types_path = os.path.join(apache_config_dir, 'mime.types')
    document_root = os.path.abspath(options.document_root)

    start_cmd = platform_util.GetStartHttpdCommand(output_dir,
                                                   httpd_conf_path,
                                                   mime_types_path,
                                                   document_root)
    stop_cmd = platform_util.GetStopHttpdCommand()
    http_server = google.httpd_utils.ApacheHttpd(start_cmd, stop_cmd, [8000])
    try:
      http_server.StartServer()
    except google.httpd_utils.HttpdNotStarted, e:
      # Improve the error message.
      raise google.httpd_utils.HttpdNotStarted('%s. See log file in %s' %
                                               (e, output_dir))

  if options.enable_pageheap:
    slave_utils.SetPageHeap(build_dir, 'chrome.exe', True)

  if options.parallel:
    launcher_path = os.path.join(build_dir, '..', 'tools',
                                 'parallel_launcher', 'parallel_launcher.py')
    command = ['python.exe', launcher_path, test_exe_path]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  chromium_utils.RemoveChromeTemporaryFiles()

  results_tracker = None
  if options.generate_json_file:
    results_tracker = GTestUnexpectedDeathTracker()

    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  result = _RunGTestCommand(command, results_tracker)

  if options.document_root:
    http_server.StopServer()

  if options.enable_pageheap:
    slave_utils.SetPageHeap(build_dir, 'chrome.exe', False)

  if options.generate_json_file:
    _GenerateJSONForTestResults(options, results_tracker)

  return result


def main():
  # Initialize logging.
  log_level = logging.INFO
  logging.basicConfig(level=log_level,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')

  option_parser = optparse.OptionParser(usage=USAGE)

  # Since the trailing program to run may have has command-line args of its
  # own, we need to stop parsing when we reach the first positional argument.
  option_parser.disable_interspersed_args()

  option_parser.add_option('', '--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('', '--build-dir', default='chrome',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('', '--enable-pageheap', action='store_true',
                           default=False,
                           help='enable pageheap checking for chrome.exe')
  option_parser.add_option('', '--with-httpd', dest='document_root',
                           default=None, metavar='DOC_ROOT',
                           help='Start a local httpd server using the given '
                                'document root, relative to the current dir')
  option_parser.add_option('', '--total-shards', dest='total_shards',
                           default=None, type="int",
                           help='Number of shards to split this test into.')
  option_parser.add_option('', '--shard-index', dest='shard_index',
                           default=None, type="int",
                           help='Shard to run. Must be between 1 and '
                                'total-shards.')
  option_parser.add_option('', '--run-shell-script', action='store_true',
                           default=False,
                           help='treat first argument as the shell script'
                                'to run.')
  option_parser.add_option('', '--generate-json-file', action='store_true',
                           default=False,
                           help='output JSON results file if specified.')
  option_parser.add_option('--parallel', action='store_true',
                           help='run tests in parallel for speed')
  option_parser.add_option('-o', '--results-directory', default='',
                           help='output results directory for JSON file.')
  option_parser.add_option("", "--builder-name", default=None,
                           help="The name of the builder running this script.")
  option_parser.add_option("", "--build-number", default=None,
                           help=("The build number of the builder running"
                                 "this script."))
  option_parser.add_option("", "--test-type", default='',
                           help="The test name that identifies the test, "
                                "e.g. 'unit-tests'")
  options, args = option_parser.parse_args()

  # Print out builder name for log_parser
  print '[Running on builder: "%s"]' % options.builder_name

  # Set the number of shards environement variables.
  if options.total_shards and options.shard_index:
    os.environ['GTEST_TOTAL_SHARDS'] = str(options.total_shards)
    os.environ['GTEST_SHARD_INDEX'] = str(options.shard_index - 1)

  if options.results_directory:
    options.test_output_xml = os.path.normpath(os.path.join(
        options.results_directory, '%s.xml' % options.test_type))
    args.append('--gtest_output=xml:' + options.test_output_xml)

  if sys.platform.startswith('darwin'):
    return main_mac(options, args)
  elif sys.platform == 'win32':
    return main_win(options, args)
  elif sys.platform == 'linux2':
    return main_linux(options, args)
  else:
    sys.stderr.write('Unknown sys.platform value %s\n' % repr(sys.platform))
    return 1


if '__main__' == __name__:
  sys.exit(main())
