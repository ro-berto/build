#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
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
import stat
import sys
import tempfile

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
from slave import gtest_slave_utils
from slave import slave_utils
from slave import xvfb
import config

USAGE = '%s [options] test.exe [test args]' % os.path.basename(sys.argv[0])

CHROME_SANDBOX_PATH = '/opt/chromium/chrome_sandbox'

DEST_DIR = 'gtest_results'

HTTPD_CONF = {
    'linux': 'httpd2_linux.conf',
    'mac': 'httpd2_mac.conf',
    'win': 'httpd.conf'
}

def should_enable_sandbox(sandbox_path):
  """Return a boolean indicating that the current slave is capable of using the
  sandbox and should enable it.  This should return True iff the slave is a
  Linux host with the sandbox file present and configured correctly."""
  if not (sys.platform.startswith('linux') and
          os.path.exists(sandbox_path)):
    return False
  sandbox_stat = os.stat(sandbox_path)
  if ((sandbox_stat.st_mode & stat.S_ISUID) and
      (sandbox_stat.st_mode & stat.S_IRUSR) and
      (sandbox_stat.st_mode & stat.S_IXUSR) and
      (sandbox_stat.st_uid == 0)):
    return True
  return False

def get_temp_count():
  """Returns the number of files and directories inside the temporary dir."""
  return len(os.listdir(tempfile.gettempdir()))


def _RunGTestCommand(command, results_tracker=None, pipes=None):
  if results_tracker and pipes:
    # This is not supported by RunCommand.
    print 'Invalid test invocation. (results_tracker and pipes)'
    return 1
  if results_tracker:
    return chromium_utils.RunCommand(
        command, parser_func=results_tracker.OnReceiveLine)
  else:
    return chromium_utils.RunCommand(command, pipes=pipes)


def _GenerateJSONForTestResults(options, results_tracker):
  """Generate (update) a JSON file from the gtest results XML and
  upload the file to the archive server.
  The archived JSON file will be placed at:
  www-dir/DEST_DIR/buildname/testname/results.json
  on the archive server (NOTE: this is to be deprecated).
  Note that it adds slave's WebKit/Tools/Scripts to the PYTHONPATH
  to run the JSON generator.

  Args:
    options: command-line options that are supposed to have build_dir,
        results_directory, builder_name, build_name and test_output_xml values.
  """
  # pylint: disable=W0703
  results_map = None
  try:
    if os.path.exists(options.test_output_xml):
      results_map = gtest_slave_utils.GetResultsMapFromXML(
          options.test_output_xml)
    else:
      sys.stderr.write('Unable to generate JSON from XML, using log output.')
      # The file did not get generated. See if we can generate a results map
      # from the log output.
      results_map = results_tracker.GetResultsMap()
  except Exception, e:
    # This error will be caught by the following 'not results_map' statement.
    print 'Error: ', e

  if not results_map:
    print 'No data was available to update the JSON results'
    return

  build_dir = os.path.abspath(options.build_dir)
  slave_name = slave_utils.SlaveBuildName(build_dir)

  generate_json_options = copy.copy(options)
  generate_json_options.build_name = slave_name
  generate_json_options.input_results_xml = options.test_output_xml
  generate_json_options.builder_base_url = '%s/%s/%s/%s' % (
      config.Master.archive_url, DEST_DIR, slave_name, options.test_type)
  generate_json_options.master_name = slave_utils.GetActiveMaster()
  generate_json_options.test_results_server = config.Master.test_results_server

  # Print out master name for log_parser
  print '[Running for master: "%s"]' % generate_json_options.master_name

  try:
    # Set webkit and chrome directory (they are used only to get the
    # repository revisions).
    generate_json_options.webkit_dir = chromium_utils.FindUpward(
        build_dir, 'third_party', 'WebKit', 'Source')
    generate_json_options.chrome_dir = build_dir

    # Generate results JSON file and upload it to the appspot server.
    gtest_slave_utils.GenerateAndUploadJSONResults(
        results_map, generate_json_options)

    # The code can throw all sorts of exceptions, including
    # slave.gtest.networktransaction.NetworkTimeout so just trap everything.
  except:  # pylint: disable=W0702
    print 'Unexpected error while generating JSON'

def _BuildParallelCommand(build_dir, test_exe_path, options):
  supervisor_path = os.path.join(build_dir, '..', 'tools',
                                 'sharding_supervisor',
                                 'sharding_supervisor.py')
  supervisor_args = ['--no-color']
  if options.factory_properties.get('retry_failed', True):
    supervisor_args.append('--retry-failed')
  if options.total_shards and options.shard_index:
    supervisor_args.extend(['--total-slaves', str(options.total_shards),
                            '--slave-index', str(options.shard_index - 1)])
  if options.sharding_args:
    supervisor_args.extend(options.sharding_args.split())
  command = [sys.executable, supervisor_path]
  command.extend(supervisor_args)
  command.append(test_exe_path)
  return command

def start_http_server(platform, build_dir, test_exe_path, document_root):
  # pylint: disable=F0401
  import google.httpd_utils
  import google.platform_utils
  platform_util = google.platform_utils.PlatformUtility(build_dir)

  # Name the output directory for the exe, without its path or suffix.
  # e.g., chrome-release/httpd_logs/unit_tests/
  test_exe_name = os.path.splitext(os.path.basename(test_exe_path))[0]
  output_dir = os.path.join(slave_utils.SlaveBaseDir(build_dir),
                            'httpd_logs',
                            test_exe_name)

  # Sanity checks for httpd2_linux.conf.
  if platform == 'linux':
    for ssl_file in ['ssl.conf', 'ssl.load']:
      ssl_path = os.path.join('/etc/apache/mods-enabled', ssl_file)
      if not os.path.exists(ssl_path):
        sys.stderr.write('WARNING: %s missing, http server may not start\n' %
                         ssl_path)
    if not os.access('/var/run/apache2', os.W_OK):
      sys.stderr.write('WARNING: cannot write to /var/run/apache2, '
                       'http server may not start\n')

  apache_config_dir = google.httpd_utils.ApacheConfigDir(build_dir)
  httpd_conf_path = os.path.join(apache_config_dir, HTTPD_CONF[platform])
  mime_types_path = os.path.join(apache_config_dir, 'mime.types')
  document_root = os.path.abspath(document_root)

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
  return http_server

def main_mac(options, args):
  if len(args) < 1:
    raise chromium_utils.MissingArgument('Usage: %s' % USAGE)

  test_exe = args[0]
  build_dir = os.path.normpath(os.path.abspath(options.build_dir))
  test_exe_path = os.path.join(build_dir, options.target, test_exe)
  if not os.path.exists(test_exe_path):
    pre = 'Unable to find %s\n' % test_exe_path

    build_dir = os.path.dirname(build_dir)
    outdir = 'xcodebuild'
    is_make_or_ninja = (options.factory_properties.get("gclient_env", {})
        .get('GYP_GENERATORS', '') in ('ninja', 'make'))
    if is_make_or_ninja:
      outdir = 'out'

    build_dir = os.path.join(build_dir, outdir)
    test_exe_path = os.path.join(build_dir, options.target, test_exe)
    if not os.path.exists(test_exe_path):
      msg = pre + 'Unable to find %s' % test_exe_path
      if options.factory_properties.get('succeed_on_missing_exe', False):
        print '%s missing but succeed_on_missing_exe used, exiting' % (
            test_exe_path)
        return 0
      raise chromium_utils.PathNotFound(msg)

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  if options.parallel:
    command = _BuildParallelCommand(build_dir, test_exe_path, options)
  elif options.run_shell_script:
    command = ['bash', test_exe_path]
  elif options.run_python_script:
    command = [sys.executable, test_exe]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  results_tracker = None
  if options.generate_json_file:
    results_tracker = gtest_slave_utils.GTestUnexpectedDeathTracker()

    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  try:
    http_server = None
    if options.document_root:
      http_server = start_http_server('mac', build_dir=build_dir,
                                      test_exe_path=test_exe_path,
                                      document_root=options.document_root)
    if options.factory_properties.get('asan', False):
      symbolize = os.path.abspath(os.path.join('src', 'tools', 'valgrind',
                                               'asan', 'asan_symbolize.py'))
      pipes = [[sys.executable, symbolize], ['c++filt']]
      result = _RunGTestCommand(command, pipes=pipes)
    else:
      result = _RunGTestCommand(command, results_tracker)
  finally:
    if http_server:
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

  # Figure out what we want for a special frame buffer directory.
  special_xvfb_dir = None
  if options.special_xvfb == 'auto':
    fp_special_xvfb = options.factory_properties.get('special_xvfb', None)
    fp_chromeos = options.factory_properties.get('chromeos', None)
    if fp_special_xvfb or (fp_special_xvfb is None and (fp_chromeos or
        slave_utils.GypFlagIsOn(options, 'use_aura') or
        slave_utils.GypFlagIsOn(options, 'chromeos'))):
      special_xvfb_dir = options.special_xvfb_dir
  elif options.special_xvfb:
    special_xvfb_dir = options.special_xvfb_dir

  test_exe = args[0]
  test_exe_path = os.path.join(bin_dir, test_exe)
  if not os.path.exists(test_exe_path):
    if options.factory_properties.get('succeed_on_missing_exe', False):
      print '%s missing but succeed_on_missing_exe used, exiting' % (
          test_exe_path)
      return 0
    msg = 'Unable to find %s' % test_exe_path
    raise chromium_utils.PathNotFound(msg)

  # Decide whether to enable the suid sandbox for Chrome.
  if should_enable_sandbox(CHROME_SANDBOX_PATH):
    print 'Enabling sandbox.  Setting environment variable:'
    print '  CHROME_DEVEL_SANDBOX="%s"' % CHROME_SANDBOX_PATH
    os.environ['CHROME_DEVEL_SANDBOX'] = CHROME_SANDBOX_PATH
  else:
    print 'Disabling sandbox.  Setting environment variable:'
    print '  CHROME_DEVEL_SANDBOX=""'
    os.environ['CHROME_DEVEL_SANDBOX'] = ''

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  os.environ['LD_LIBRARY_PATH'] = '%s:%s/lib:%s/lib.target' % (bin_dir, bin_dir,
                                                               bin_dir)
  # Figure out what we want for a special llvmpipe directory.
  if (options.llvmpipe_dir and os.path.exists(options.llvmpipe_dir)):
    os.environ['LD_LIBRARY_PATH'] += ':' + options.llvmpipe_dir

  if options.parallel:
    command = _BuildParallelCommand(build_dir, test_exe_path, options)
  elif options.run_shell_script:
    command = ['bash', test_exe_path]
  elif options.run_python_script:
    command = [sys.executable, test_exe]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  results_tracker = None
  if options.generate_json_file:
    results_tracker = gtest_slave_utils.GTestUnexpectedDeathTracker()

    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  try:
    http_server = None
    if options.document_root:
      http_server = start_http_server('linux', build_dir=build_dir,
                                      test_exe_path=test_exe_path,
                                      document_root=options.document_root)
    if options.xvfb:
      xvfb.StartVirtualX(
          slave_name, bin_dir,
          with_wm=options.factory_properties.get('window_manager', True),
          server_dir=special_xvfb_dir)
    if options.factory_properties.get('asan', False):
      symbolize = os.path.abspath(os.path.join('src', 'tools', 'valgrind',
                                               'asan', 'asan_symbolize.py'))
      pipes = [[sys.executable, symbolize], ['c++filt']]
      result = _RunGTestCommand(command, pipes=pipes)
    else:
      result = _RunGTestCommand(command, results_tracker)
  finally:
    if http_server:
      http_server.StopServer()
    if options.xvfb:
      xvfb.StopVirtualX(slave_name)

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
    if options.factory_properties.get('succeed_on_missing_exe', False):
      print '%s missing but succeed_on_missing_exe used, exiting' % (
          test_exe_path)
      return 0
    raise chromium_utils.PathNotFound('Unable to find %s' % test_exe_path)

  if options.enable_pageheap:
    slave_utils.SetPageHeap(build_dir, 'chrome.exe', True)

  if options.parallel:
    command = _BuildParallelCommand(build_dir, test_exe_path, options)
  elif options.run_python_script:
    command = [sys.executable, test_exe]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  results_tracker = None
  if options.generate_json_file:
    results_tracker = gtest_slave_utils.GTestUnexpectedDeathTracker()

    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  try:
    http_server = None
    if options.document_root:
      http_server = start_http_server('win', build_dir=build_dir,
                                      test_exe_path=test_exe_path,
                                      document_root=options.document_root)
    result = _RunGTestCommand(command, results_tracker)
  finally:
    if http_server:
      http_server.StopServer()

  if options.enable_pageheap:
    slave_utils.SetPageHeap(build_dir, 'chrome.exe', False)

  if options.generate_json_file:
    _GenerateJSONForTestResults(options, results_tracker)

  return result


def main():
  import platform

  xvfb_path = os.path.join(os.path.dirname(sys.argv[0]), '..', '..',
                           'third_party', 'xvfb', platform.architecture()[0])

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
  # --with-httpd assumes a chromium checkout with src/tools/python.
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
  option_parser.add_option('', '--run-python-script', action='store_true',
                           default=False,
                           help='treat first argument as a python script'
                                'to run.')
  option_parser.add_option('', '--generate-json-file', action='store_true',
                           default=False,
                           help='output JSON results file if specified.')
  option_parser.add_option('', '--parallel', action='store_true',
                           help='Shard and run tests in parallel for speed '
                                'with sharding_supervisor.')
  option_parser.add_option('', '--llvmpipe', action='store_const',
                           const=xvfb_path, dest='llvmpipe_dir',
                           help='Use software gpu pipe directory.')
  option_parser.add_option('', '--no-llvmpipe', action='store_const',
                           const=None, dest='llvmpipe_dir',
                           help='Do not use software gpu pipe directory.')
  option_parser.add_option('', '--llvmpipe-dir',
                           default=None, dest='llvmpipe_dir',
                           help='Path to software gpu library directory.')
  option_parser.add_option('', '--special-xvfb-dir', default=xvfb_path,
                           help='Path to virtual X server directory on Linux.')
  option_parser.add_option('', '--special-xvfb', action='store_true',
                           default='auto',
                           help='use non-default virtual X server on Linux.')
  option_parser.add_option('', '--no-special-xvfb', action='store_false',
                           dest='special_xvfb',
                           help='Use default virtual X server on Linux.')
  option_parser.add_option('', '--auto-special-xvfb', action='store_const',
                           const='auto', dest='special_xvfb',
                           help='Guess as to virtual X server on Linux.')
  option_parser.add_option('', '--xvfb', action='store_true', dest='xvfb',
                           default=True,
                           help='Start virtual X server on Linux.')
  option_parser.add_option('', '--no-xvfb', action='store_false', dest='xvfb',
                           help='Do not start virtual X server on Linux.')
  option_parser.add_option('', '--sharding-args', dest='sharding_args',
                           default=None,
                           help='Options to pass to sharding_supervisor.')
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
  option_parser.add_option("", "--test-results-server", default='',
                           help="The test results server to upload the "
                                "results.")
  chromium_utils.AddPropertiesOptions(option_parser)
  options, args = option_parser.parse_args()

  if options.run_shell_script and options.run_python_script:
    sys.stderr.write('Use either --run-shell-script OR --run-python-script, '
                     'not both.')
    return 1

  # Print out builder name for log_parser
  print '[Running on builder: "%s"]' % options.builder_name

  if options.factory_properties.get('asan', False):
    # Instruct GTK to use malloc while running ASAN tests.
    os.environ['G_SLICE'] = 'always-malloc'
    # Disable ASLR on Mac when running ASAN tests.
    os.environ['DYLD_NO_PIE'] = '1'
  # Set the number of shards environement variables.
  if options.total_shards and options.shard_index:
    os.environ['GTEST_TOTAL_SHARDS'] = str(options.total_shards)
    os.environ['GTEST_SHARD_INDEX'] = str(options.shard_index - 1)

  if options.results_directory:
    options.test_output_xml = os.path.normpath(os.path.join(
        options.results_directory, '%s.xml' % options.test_type))
    args.append('--gtest_output=xml:' + options.test_output_xml)

  temp_files = get_temp_count()
  if sys.platform.startswith('darwin'):
    result = main_mac(options, args)
  elif sys.platform == 'win32':
    result = main_win(options, args)
  elif sys.platform == 'linux2':
    result = main_linux(options, args)
  else:
    sys.stderr.write('Unknown sys.platform value %s\n' % repr(sys.platform))
    return 1

  new_temp_files = get_temp_count()
  if temp_files > new_temp_files:
    print >> sys.stderr, (
        'Confused: %d files were deleted from %s during the test run') % (
        (temp_files - new_temp_files), tempfile.gettempdir())
  elif temp_files < new_temp_files:
    print >> sys.stderr, (
        '%d new files were left in %s: Fix the tests to clean up themselves.'
        ) % ((new_temp_files - temp_files), tempfile.gettempdir())
    # TODO(maruel): Make it an error soon. Not yet since I want to iron out all
    # the remaining cases before.
    #result = 1
  return result


if '__main__' == __name__:
  sys.exit(main())
