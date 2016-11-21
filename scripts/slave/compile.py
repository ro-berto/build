#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to build chrome, executed by buildbot.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import multiprocessing
import optparse
import os
import signal
import subprocess
import sys

from common import chromium_utils
from slave import build_directory
from slave import goma_utils
from slave import update_windows_env

# Define a bunch of directory paths (same as bot_update.py)
CURRENT_DIR = os.path.abspath(os.getcwd())
BUILDER_DIR = os.path.dirname(CURRENT_DIR)
SLAVE_DIR = os.path.dirname(BUILDER_DIR)
# GOMA_CACHE_DIR used for caching long-term data.
DEFAULT_GOMA_CACHE_DIR = os.path.join(SLAVE_DIR, 'goma_cache')

# Path of the scripts/slave/ checkout on the slave, found by looking at the
# current compile.py script's path's dirname().
SLAVE_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
# Path of the build/ checkout on the slave, found relative to the
# scripts/slave/ directory.
BUILD_DIR = os.path.dirname(os.path.dirname(SLAVE_SCRIPTS_DIR))


class EchoDict(dict):
  """Dict that remembers all modified values."""

  def __init__(self, *args, **kwargs):
    self.overrides = set()
    self.adds = set()
    super(EchoDict, self).__init__(*args, **kwargs)

  def __setitem__(self, key, val):
    if not key in self and not key in self.overrides:
      self.adds.add(key)
    self.overrides.add(key)
    super(EchoDict, self).__setitem__(key, val)

  def __delitem__(self, key):
    self.overrides.add(key)
    if key in self.adds:
      self.adds.remove(key)
      self.overrides.remove(key)
    super(EchoDict, self).__delitem__(key)

  def print_overrides(self, fh=None):
    if not self.overrides:
      return
    if not fh:
      fh = sys.stdout
    fh.write('Environment variables modified in compile.py:\n')
    for k in sorted(list(self.overrides)):
      if k in self:
        fh.write('  %s=%s\n' % (k, self[k]))
      else:
        fh.write('  %s (removed)\n' % k)
    fh.write('\n')


def StopGomaClientAndUploadInfo(options, env, exit_status):
  """Stop goma compiler_proxy and upload goma-related information.

  Args:
    options (Option) : options to specify where to store goma-related info.
    env (dict)       : used when goma_ctl command executes.
    exit_status (int): exit_status sent to monitoring system.
  """
  goma_ctl_cmd = [sys.executable,
                  os.path.join(options.goma_dir, 'goma_ctl.py')]

  if options.goma_jsonstatus:
    chromium_utils.RunCommand(
        goma_ctl_cmd + ['jsonstatus', options.goma_jsonstatus], env=env)
    goma_utils.SendGomaTsMon(options.goma_jsonstatus, exit_status,
                             builder=options.buildbot_buildername,
                             master=options.buildbot_mastername,
                             slave=options.buildbot_slavename,
                             clobber=options.buildbot_clobber)

  # If goma compiler_proxy crashes, there could be crash dump.
  if options.build_data_dir:
    env['GOMACTL_CRASH_REPORT_ID_FILE'] = os.path.join(options.build_data_dir,
                                                       'crash_report_id_file')
  # We must stop the proxy to dump GomaStats.
  chromium_utils.RunCommand(goma_ctl_cmd + ['stop'], env=env)
  override_gsutil = None
  if options.gsutil_py_path:
    # Needs to add '--', otherwise gsutil options will be passed to gsutil.py.
    override_gsutil = [sys.executable, options.gsutil_py_path, '--']
  goma_utils.UploadGomaCompilerProxyInfo(override_gsutil=override_gsutil,
                                         builder=options.buildbot_buildername,
                                         master=options.buildbot_mastername,
                                         slave=options.buildbot_slavename,
                                         clobber=options.buildbot_clobber)

  # Upload GomaStats to make it monitored.
  if env.get('GOMA_DUMP_STATS_FILE'):
    goma_utils.SendGomaStats(env['GOMA_DUMP_STATS_FILE'],
                             env.get('GOMACTL_CRASH_REPORT_ID_FILE'),
                             options.build_data_dir)

# TODO(tikuta): move to goma_utils.py
def goma_setup(options, env):
  """Sets up goma if necessary.

  If using the Goma compiler, first call goma_ctl to ensure the proxy is
  available, and returns (True, instance of cloudtail subprocess).
  If it failed to start up compiler_proxy, modify options.compiler
  and options.goma_dir, modify env to GOMA_DISABLED=true,
  and returns (False, None).
  """
  cloudtail_pid_file = options.cloudtail_pid_file

  if cloudtail_pid_file and os.path.exists(cloudtail_pid_file):
    os.remove(cloudtail_pid_file)

  if options.compiler not in ('goma', 'goma-clang'):
    # Unset goma_dir to make sure we'll not use goma.
    options.goma_dir = None
    return False, None

  if options.goma_fail_fast:
    # startup fails when initial ping failed.
    env['GOMA_FAIL_FAST'] = 'true'
  else:
    # If a network error continues 30 minutes, compiler_proxy make the compile
    # failed.  When people use goma, they expect using goma is faster than
    # compile locally. If goma cannot guarantee that, let it make compile
    # as error.
    env['GOMA_ALLOWED_NETWORK_ERROR_DURATION'] = '1800'

  if options.goma_max_active_fail_fallback_tasks:
    env['GOMA_MAX_ACTIVE_FAIL_FALLBACK_TASKS'] = (
        options.goma_max_active_fail_fallback_tasks)

  # Caches CRLs in GOMA_CACHE_DIR.
  # Since downloading CRLs is usually slow, caching them may improves
  # compiler_proxy start time.
  if not os.path.exists(options.goma_cache_dir):
    os.mkdir(options.goma_cache_dir, 0700)
  env['GOMA_CACHE_DIR'] = options.goma_cache_dir

  # Enable DepsCache. DepsCache caches the list of files to send goma server.
  # This will greatly improve build speed when cache is warmed.
  if options.goma_deps_cache_file:
    env['GOMA_DEPS_CACHE_FILE'] = options.goma_deps_cache_file
  else:
    # TODO(shinyak): GOMA_DEPS_CACHE_DIR will be removed from goma in future.
    # GOMA_DEPS_CACHE_FILE should be used.
    env['GOMA_DEPS_CACHE_DIR'] = (
      options.goma_deps_cache_dir or options.target_output_dir)

  if options.goma_hermetic:
    env['GOMA_HERMETIC'] = options.goma_hermetic
  if options.goma_enable_remote_link:
    env['GOMA_ENABLE_REMOTE_LINK'] = options.goma_enable_remote_link
  if options.goma_store_local_run_output:
    env['GOMA_STORE_LOCAL_RUN_OUTPUT'] = options.goma_store_local_run_output

  if options.build_data_dir:
    env['GOMA_DUMP_STATS_FILE'] = os.path.join(options.build_data_dir,
                                               'goma_stats_proto')

  if options.goma_service_account_json_file:
    env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = \
        options.goma_service_account_json_file
  goma_start_command = ['restart']
  goma_ctl_cmd = [sys.executable,
                  os.path.join(options.goma_dir, 'goma_ctl.py')]
  result = chromium_utils.RunCommand(goma_ctl_cmd + goma_start_command, env=env)
  if not result:
    # goma started sucessfully.
    # Making cloudtail to upload the latest log.
    # TODO(yyanagisawa): install cloudtail from CIPD.

    # TODO(vadimsh): crbug/642299
    return True, None

  StopGomaClientAndUploadInfo(options, env, -1)

  if options.goma_disable_local_fallback:
    print 'error: failed to start goma; fallback has been disabled'
    raise Exception('failed to start goma')

  print 'warning: failed to start goma. falling back to non-goma'
  # Drop goma from options.compiler
  options.compiler = options.compiler.replace('goma-', '')
  if options.compiler == 'goma':
    options.compiler = None
  # Reset options.goma_dir.
  options.goma_dir = None
  env['GOMA_DISABLED'] = '1'
  return False, None


# TODO(tikuta): move to goma_utils.py
def goma_teardown(options, env, exit_status, cloudtail_proc):
  """Tears down goma if necessary. """
  cloudtail_pid_file = options.cloudtail_pid_file

  if options.goma_dir:
    StopGomaClientAndUploadInfo(options, env, exit_status)

  if cloudtail_proc:
    cloudtail_proc.terminate()
    cloudtail_proc.wait()
  elif cloudtail_pid_file:
    with open(cloudtail_pid_file) as f:
      pid = int(f.read())
      os.kill(pid, signal.SIGTERM)
    os.remove(cloudtail_pid_file)


def maybe_set_official_build_envvars(options, env):
  if options.mode == 'google_chrome' or options.mode == 'official':
    env['CHROMIUM_BUILD'] = '_google_chrome'

  if options.mode == 'official':
    # Official builds are always Google Chrome.
    env['CHROME_BUILD_TYPE'] = '_official'


class EnsureUpToDateFilter(chromium_utils.RunCommandFilter):
  """Filter for RunCommand that checks whether the output contains ninja's
  message for a no-op build."""
  def __init__(self):
    self.was_up_to_date = False

  def FilterLine(self, a_line):
    if 'ninja: no work to do.' in a_line:
      self.was_up_to_date = True
    return a_line


# TODO(tikuta): move to goma_utils
def determine_goma_jobs():
  # We would like to speed up build on Windows a bit, since it is slowest.
  number_of_processors = 0
  try:
    number_of_processors = multiprocessing.cpu_count()
  except NotImplementedError:
    print 'cpu_count() is not implemented, using default value 50.'
    return 50

  assert number_of_processors > 0

  # When goma is used, 10 * number_of_processors is basically good in
  # various situations according to our measurement. Build speed won't
  # be improved if -j is larger than that.
  #
  # Since Mac had process number limitation before, we had to set
  # the upper limit to 50. Now that the process number limitation is 2000,
  # so we would be able to use 10 * number_of_processors.
  # For safety, we'd like to set the upper limit to 200.
  #
  # Note that currently most try-bot build slaves have 8 processors.
  if chromium_utils.IsMac() or chromium_utils.IsWindows():
    return min(10 * number_of_processors, 200)

  # For Linux, we also would like to use 10 * cpu. However, not sure
  # backend resource is enough, so let me set Linux and Linux x64 builder
  # only for now.
  hostname = goma_utils.GetShortHostname()
  if hostname in (
      ['build14-m1', 'build48-m1'] +
      # Also increasing cpus for v8/blink trybots.
      ['build%d-m4' % x for x in xrange(45, 48)] +
      # Also increasing cpus for LTO buildbots.
      ['slave%d-c1' % x for x in [20, 33] + range(78, 108)] +
      # Also increasing cpus for Findit trybots.
      ['slave%d-c4' % x for x in [799] + range(873, 878)]):
    return min(10 * number_of_processors, 200)

  return 50


def main_ninja(options, args, env):
  """This function calls ninja.

  Args:
      options (Option): options for ninja command.
      args (str): extra args for ninja command.
      env (dict): Used when ninja command executes.

  Returns:
      int: ninja command exit status.

  """

  exit_status = -1

  try:
    print 'chdir to %s' % options.src_dir
    os.chdir(options.src_dir)

    command = [options.ninja_path, '-w', 'dupbuild=err',
                                   '-C', options.target_output_dir]

    # HACK(yyanagisawa): update environment files on |env| update.
    # For compiling on Windows, environment in environment files are used.
    # It means even if enviroment such as GOMA_DISABLED is updated in
    # compile.py, the update will be ignored.
    # We need to update environment files to reflect the update.
    if (chromium_utils.IsWindows() and
        update_windows_env.NeedEnvFileUpdateOnWin(env.overrides)):
      print 'Updating environment.{x86,x64} files.'
      update_windows_env.UpdateWindowsEnvironment(
          options.target_output_dir, env, env.overrides)

    if options.clobber:
      print 'Removing %s' % options.target_output_dir
      # Deleting output_dir would also delete all the .ninja files necessary to
      # build. Clobbering should run before runhooks (which creates .ninja
      # files). For now, only delete all non-.ninja files.
      # TODO(thakis): Make "clobber" a step that runs before "runhooks".
      # Once the master has been restarted, remove all clobber handling
      # from compile.py, https://crbug.com/574557
      build_directory.RmtreeExceptNinjaOrGomaFiles(options.target_output_dir)

    command.extend(options.build_args)
    command.extend(args)

    maybe_set_official_build_envvars(options, env)

    if options.compiler:
      print 'using', options.compiler

    if options.compiler in ('goma', 'goma-clang'):
      assert options.goma_dir
      assert options.goma_jobs
      command.append('-j%d' % options.goma_jobs)

    # Run the build.
    env.print_overrides()
    exit_status = chromium_utils.RunCommand(command, env=env)
    if exit_status == 0:
      # Run the build again if we want to check that the no-op build is clean.
      filter_obj = EnsureUpToDateFilter()
      # Append `-d explain` to help diagnose in the failure case.
      command += ['-d', 'explain', '-n']
      chromium_utils.RunCommand(command, env=env, filter_obj=filter_obj)
      if not filter_obj.was_up_to_date and options.ninja_ensure_up_to_date:
        print 'Failing build because ninja reported work to do.'
        print 'This means that after completing a compile, another was run and'
        print 'it resulted in still having work to do (that is, a no-op build'
        print 'wasn\'t a no-op). Consult the first "ninja explain:" line for a'
        print 'likely culprit.'
        return 1
    return exit_status
  finally:
    override_gsutil = None
    if options.gsutil_py_path:
      # Needs to add '--', otherwise gsutil options will be passed to gsutil.py.
      override_gsutil = [sys.executable, options.gsutil_py_path, '--']

    goma_utils.UploadNinjaLog(
        options.target_output_dir, options.compiler, command, exit_status,
        override_gsutil=override_gsutil)


def get_target_build_dir(options):
  """Keep this function in sync with src/build/landmines.py"""
  if chromium_utils.IsLinux() and options.cros_board:
    # When building ChromeOS's Simple Chrome workflow, the output directory
    # has a CROS board name suffix.
    outdir = 'out_%s' % (options.cros_board,)
  elif options.out_dir:
    outdir = options.out_dir
  else:
    outdir = 'out'
  return os.path.abspath(os.path.join(options.src_dir, outdir, options.target))


def get_parsed_options():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--clobber', action='store_true', default=False,
                           help='delete the output directory before compiling')
  option_parser.add_option('--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('--src-dir', default=None,
                           help='path to the root of the source tree')
  option_parser.add_option('--mode', default='dev',
                           help='build mode (dev or official) controlling '
                                'environment variables set during build')
  # TODO(thakis): Remove this, https://crbug.com/622768
  option_parser.add_option('--build-tool', default=None, help='ignored')
  option_parser.add_option('--build-args', action='append', default=[],
                           help='arguments to pass to the build tool')
  option_parser.add_option('--build-data-dir', action='store',
                           help='specify a build data directory.')
  option_parser.add_option('--compiler', default=None,
                           help='specify alternative compiler (e.g. clang)')
  if chromium_utils.IsLinux():
    option_parser.add_option('--cros-board', action='store',
                             help='If building for the ChromeOS Simple Chrome '
                                  'workflow, the name of the ChromeOS board.')
  option_parser.add_option('--out-dir', action='store',
                           help='Specify a custom output directory.')
  option_parser.add_option('--goma-dir',
                           default=os.path.join(BUILD_DIR, 'goma'),
                           help='specify goma directory')
  option_parser.add_option('--goma-cache-dir',
                           default=DEFAULT_GOMA_CACHE_DIR,
                           help='specify goma cache directory')
  option_parser.add_option('--goma-deps-cache-file',
                           help='specify goma deps cache file')
  option_parser.add_option('--goma-deps-cache-dir',
                           help='specify goma deps cache directory. '
                                'DEPRECATED. Use --goma-deps-cache-file')
  option_parser.add_option('--goma-hermetic', default='error',
                           help='Set goma hermetic mode')
  option_parser.add_option('--goma-enable-remote-link', default=None,
                           help='Enable goma remote link.')
  option_parser.add_option('--goma-store-local-run-output', default=None,
                           help='Store local run output to goma servers.')
  option_parser.add_option('--goma-fail-fast', action='store_true')
  option_parser.add_option('--goma-disable-local-fallback', action='store_true')
  option_parser.add_option('--goma-jsonstatus',
                           help='Specify a file to dump goma_ctl jsonstatus.')
  option_parser.add_option('--goma-service-account-json-file',
                           help='Specify a file containing goma service account'
                                ' credentials')
  option_parser.add_option('--goma-max-active-fail-fallback-tasks',
                           help='Specify GOMA_MAX_ACTIVE_FAIL_FALLBACK_TASKS '
                                'for goma')
  option_parser.add_option('--goma-jobs', default=None,
                           help='The number of jobs for ninja -j.')
  option_parser.add_option('--gsutil-py-path',
                           help='Specify path to gsutil.py script '
                                'in depot_tools.')
  option_parser.add_option('--ninja-path', default='ninja',
                           help='Specify path to the ninja tool.')
  option_parser.add_option('--ninja-ensure-up-to-date', action='store_true',
                           help='Checks the output of the ninja builder to '
                                'confirm that a second compile immediately '
                                'the first is a no-op.')
  option_parser.add_option('--cloudtail-pid-file', default=None,
                           help='Specify a file to store pid of cloudtail')

  # Arguments to pass buildbot properties.
  option_parser.add_option('--buildbot-buildername', default='unknown',
                           help='buildbot buildername')
  option_parser.add_option('--buildbot-mastername', default='unknown',
                           help='buildbot mastername')
  option_parser.add_option('--buildbot-slavename', default='unknown',
                           help='buildbot slavename')
  option_parser.add_option('--buildbot-clobber', help='buildbot clobber')

  options, args = option_parser.parse_args()

  if not options.src_dir:
    options.src_dir = 'src'
  options.src_dir = os.path.abspath(options.src_dir)

  options.target_output_dir = get_target_build_dir(options)

  assert options.build_tool in (None, 'ninja')
  return options, args


def real_main():
  options, args = get_parsed_options()

  # Prepare environment.
  env = EchoDict(os.environ)

  # start goma
  goma_ready, goma_cloudtail = goma_setup(options, env)

  if not goma_ready:
    assert options.compiler not in ('goma', 'goma-clang')
    assert options.goma_dir is None
  elif options.goma_jobs is None:
    options.goma_jobs = determine_goma_jobs()

  # build
  exit_status = main_ninja(options, args, env)

  # stop goma
  goma_teardown(options, env, exit_status, goma_cloudtail)

  return exit_status


if '__main__' == __name__:
  sys.exit(real_main())
