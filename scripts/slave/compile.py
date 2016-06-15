#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to build chrome, executed by buildbot.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import datetime
import errno
import multiprocessing
import optparse
import os
import re
import shlex
import sys
import time

from common import chromium_utils
from slave import build_directory
from slave import goma_utils

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


def goma_setup(options, env):
  """Sets up goma if necessary.

  If using the Goma compiler, first call goma_ctl  to ensure the proxy is
  available, and returns True.
  If it failed to start up compiler_proxy, modify options.compiler and
  options.goma_dir and returns False

  """
  if options.compiler not in ('goma', 'goma-clang'):
    # Unset goma_dir to make sure we'll not use goma.
    options.goma_dir = None
    return False

  hostname = goma_utils.GetShortHostname()
  # HACK(shinyak, yyanagisawa, goma): Windows NO_NACL_GOMA (crbug.com/390764)
  # Building NaCl untrusted code using goma brings large performance
  # improvement but it sometimes cause build failure by race condition.
  # Let me enable goma build on goma canary buildslaves to confirm the issue
  # has been fixed by a workaround.
  # vm*-m4 are trybots. build*-m1 and vm*-m1 are all goma canary bots.
  if hostname in ['build28-m1', 'build58-m1', 'vm191-m1', 'vm480-m1',
                  'vm820-m1', 'vm821-m1', 'vm848-m1']:
    env['NO_NACL_GOMA'] = 'false'

  if options.goma_fail_fast:
    # startup fails when initial ping failed.
    env['GOMA_FAIL_FAST'] = 'true'
  else:
    # If a network error continues 30 minutes, compiler_proxy make the compile
    # failed.  When people use goma, they expect using goma is faster than
    # compile locally. If goma cannot guarantee that, let it make compile
    # as error.
    env['GOMA_ALLOWED_NETWORK_ERROR_DURATION'] = '1800'

  # HACK(yyanagisawa): reduce GOMA_BURST_MAX_PROCS crbug.com/592306
  # Recently, I sometimes see buildbot slave time out, one possibility I come
  # up with is burst mode use up resource.
  # Let me temporary set small values to GOMA_BURST_MAX_PROCS to confirm
  # the possibility is true or false.
  max_subprocs = '3'
  max_heavy_subprocs = '1'
  number_of_processors = 0
  try:
    number_of_processors = multiprocessing.cpu_count()
  except NotImplementedError:
    print 'cpu_count() is not implemented, using default value.'
    number_of_processors = 1
  if number_of_processors > 3:
    max_subprocs = str(number_of_processors - 1)
    max_heavy_subprocs = str(number_of_processors / 2)
  env['GOMA_BURST_MAX_SUBPROCS'] = max_subprocs
  env['GOMA_BURST_MAX_SUBPROCS_LOW'] = max_subprocs
  env['GOMA_BURST_MAX_SUBPROCS_HEAVY'] = max_heavy_subprocs

  # Caches CRLs in GOMA_CACHE_DIR.
  # Since downloading CRLs is usually slow, caching them may improves
  # compiler_proxy start time.
  if not os.path.exists(options.goma_cache_dir):
    os.mkdir(options.goma_cache_dir, 0700)
  env['GOMA_CACHE_DIR'] = options.goma_cache_dir

  # Enable DepsCache. DepsCache caches the list of files to send goma server.
  # This will greatly improve build speed when cache is warmed.
  # The cache file is stored in the target output directory.
  env['GOMA_DEPS_CACHE_DIR'] = (
      options.goma_deps_cache_dir or options.target_output_dir)

  if not env.get('GOMA_HERMETIC'):
    env['GOMA_HERMETIC'] = options.goma_hermetic
  if options.goma_enable_remote_link:
    env['GOMA_ENABLE_REMOTE_LINK'] = options.goma_enable_remote_link
  if options.goma_store_local_run_output:
    env['GOMA_STORE_LOCAL_RUN_OUTPUT'] = options.goma_store_local_run_output
  if options.goma_enable_compiler_info_cache:
    # Will be stored in GOMA_CACHE_DIR.
    env['GOMA_COMPILER_INFO_CACHE_FILE'] = 'goma-compiler-info.cache'

  if options.build_data_dir:
    env['GOMA_DUMP_STATS_FILE'] = os.path.join(options.build_data_dir,
                                               'goma_stats_proto')

  # goma is requested.
  goma_key = os.path.join(options.goma_dir, 'goma.key')
  if os.path.exists(goma_key):
    env['GOMA_API_KEY_FILE'] = goma_key
  if options.goma_service_account_json_file:
    env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = \
        options.goma_service_account_json_file
  if chromium_utils.IsWindows():
    env['GOMA_RPC_EXTRA_PARAMS'] = '?win'
  goma_start_command = ['restart']
  goma_ctl_cmd = [sys.executable,
                  os.path.join(options.goma_dir, 'goma_ctl.py')]
  result = chromium_utils.RunCommand(goma_ctl_cmd + goma_start_command, env=env)
  if not result:
    # goma started sucessfully.
    return True

  if options.goma_jsonstatus:
    chromium_utils.RunCommand(
        goma_ctl_cmd + ['jsonstatus', options.goma_jsonstatus], env=env)
    goma_utils.SendGomaTsMon(options.goma_jsonstatus, -1)

  # Try to stop compiler_proxy so that it flushes logs and stores
  # GomaStats.
  if options.build_data_dir:
    env['GOMACTL_CRASH_REPORT_ID_FILE'] = os.path.join(options.build_data_dir,
                                                       'crash_report_id_file')
  chromium_utils.RunCommand(goma_ctl_cmd + ['stop'], env=env)

  override_gsutil = None
  if options.gsutil_py_path:
    override_gsutil = [sys.executable, options.gsutil_py_path]

  # Upload compiler_proxy.INFO to investigate the reason of compiler_proxy
  # start-up failure.
  goma_utils.UploadGomaCompilerProxyInfo(override_gsutil=override_gsutil)
  # Upload GomaStats to make it monitored.
  if env.get('GOMA_DUMP_STATS_FILE'):
    goma_utils.SendGomaStats(env['GOMA_DUMP_STATS_FILE'],
                             env.get('GOMACTL_CRASH_REPORT_ID_FILE'),
                             options.build_data_dir)

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
  return False


def goma_teardown(options, env, exit_status):
  """Tears down goma if necessary. """
  if (options.compiler in ('goma', 'goma-clang') and
      options.goma_dir):
    override_gsutil = None
    if options.gsutil_py_path:
      override_gsutil = [sys.executable, options.gsutil_py_path]

    # If goma compiler_proxy crashes during the build, there could be crash
    # dump.
    if options.build_data_dir:
      env['GOMACTL_CRASH_REPORT_ID_FILE'] = os.path.join(options.build_data_dir,
                                                         'crash_report_id_file')
    goma_ctl_cmd = [sys.executable,
                    os.path.join(options.goma_dir, 'goma_ctl.py')]
    if options.goma_jsonstatus:
      chromium_utils.RunCommand(
          goma_ctl_cmd + ['jsonstatus', options.goma_jsonstatus], env=env)
      goma_utils.SendGomaTsMon(options.goma_jsonstatus, exit_status)
    # Always stop the proxy for now to allow in-place update.
    chromium_utils.RunCommand(goma_ctl_cmd + ['stop'], env=env)
    goma_utils.UploadGomaCompilerProxyInfo(override_gsutil=override_gsutil)
    if env.get('GOMA_DUMP_STATS_FILE'):
      goma_utils.SendGomaStats(env['GOMA_DUMP_STATS_FILE'],
                               env.get('GOMACTL_CRASH_REPORT_ID_FILE'),
                               options.build_data_dir)


def maybe_set_official_build_envvars(options, env):
  if options.mode == 'google_chrome' or options.mode == 'official':
    env['CHROMIUM_BUILD'] = '_google_chrome'

  if options.mode == 'official':
    # Official builds are always Google Chrome.
    env['CHROME_BUILD_TYPE'] = '_official'


def common_make_settings(command, options, env, compiler=None):
  """
  Sets desirable environment variables and command-line options that are used
  in the Make build.
  """
  assert compiler in (None, 'clang', 'goma', 'goma-clang')
  maybe_set_official_build_envvars(options, env)

  # Don't stop at the first error.
  command.append('-k')

  # Set jobs parallelization based on number of cores.
  jobs = os.sysconf('SC_NPROCESSORS_ONLN')

  if compiler in ('goma', 'goma-clang'):
    print 'using', compiler
    goma_jobs = 50
    if jobs < goma_jobs:
      jobs = goma_jobs
    command.append('-j%d' % jobs)
    return

  if compiler == 'clang':
    command.append('-r')

  command.append('-j%d' % jobs)


def main_make(options, args):
  """Interprets options, clobbers object files, and calls make.
  """

  env = EchoDict(os.environ)
  goma_ready = goma_setup(options, env)
  if not goma_ready:
    assert options.compiler not in ('goma', 'goma-clang')
    assert options.goma_dir is None

  command = ['make']
  # Try to build from <build_dir>/Makefile, or if that doesn't exist,
  # from the top-level Makefile.
  if os.path.isfile(os.path.join(options.build_dir, 'Makefile')):
    working_dir = options.build_dir
  else:
    working_dir = options.src_dir

  os.chdir(working_dir)
  common_make_settings(command, options, env, options.compiler)

  # V=1 prints the actual executed command
  if options.verbose:
    command.extend(['V=1'])
  command.extend(options.build_args + args)

  # Run the build.
  env.print_overrides()
  result = 0

  def clobber():
    print 'Removing %s' % options.target_output_dir
    chromium_utils.RemoveDirectory(options.target_output_dir)

  assert ',' not in options.target, (
   'Used to allow multiple comma-separated targets for make. This should not be'
   ' in use any more. Asserting from orbit. It\'s the only way to be sure')

  if options.clobber:
    clobber()

  target_command = command + ['BUILDTYPE=' + options.target]
  result = chromium_utils.RunCommand(target_command, env=env)
  if result and not options.clobber:
    clobber()

  goma_teardown(options, env, result)

  return result


class EnsureUpToDateFilter(chromium_utils.RunCommandFilter):
  """Filter for RunCommand that checks whether the output contains ninja's
  message for a no-op build."""
  def __init__(self):
    self.was_up_to_date = False

  def FilterLine(self, a_line):
    if 'ninja: no work to do.' in a_line:
      self.was_up_to_date = True
    return a_line


def NeedEnvFileUpdateOnWin(env):
  """Returns true if environment file need to be updated."""
  # Following GOMA_* are applied to compiler_proxy not gomacc,
  # you do not need to update environment files.
  ignore_envs = (
      'GOMA_API_KEY_FILE',
      'GOMA_DEPS_CACHE_DIR',
      'GOMA_HERMETIC',
      'GOMA_RPC_EXTRA_PARAMS',
      'GOMA_ALLOWED_NETWORK_ERROR_DURATION'
  )
  for key in env.overrides:
    if key not in ignore_envs:
      return True
  return False


def UpdateWindowsEnvironment(envfile_dir, env):
  """Update windows environment in environment.{x86,x64}.

  Args:
    envfile_dir: a directory name environment.{x86,x64} are stored.
    env: an instance of EchoDict that represents environment.
  """
  # envvars_to_save come from _ExtractImportantEnvironment in
  # https://chromium.googlesource.com/external/gyp/+/\
  # master/pylib/gyp/msvs_emuation.py
  # You must update this when the original code is updated.
  envvars_to_save = (
      'goma_.*', # TODO(scottmg): This is ugly, but needed for goma.
      'include',
      'lib',
      'libpath',
      'path',
      'pathext',
      'systemroot',
      'temp',
      'tmp',
  )
  env_to_store = {}
  for envvar in envvars_to_save:
    compiled = re.compile(envvar, re.IGNORECASE)
    for key in env.overrides:
      if compiled.match(key):
        if envvar == 'path':
          env_to_store[key] = (os.path.dirname(sys.executable) +
                               os.pathsep + env[key])
        else:
          env_to_store[key] = env[key]

  if not env_to_store:
    return

  nul = '\0'
  for arch in ['x86', 'x64']:
    path = os.path.join(envfile_dir, 'environment.%s' % arch)
    print '%s will be updated with %s.' % (path, env_to_store)
    env_in_file = {}
    with open(path) as f:
      for entry in f.read().split(nul):
        if not entry:
          continue
        key, value = entry.split('=', 1)
        env_in_file[key] = value
    env_in_file.update(env_to_store)
    with open(path, 'wb') as f:
      f.write(nul.join(['%s=%s' % (k, v) for k, v in env_in_file.iteritems()]))
      f.write(nul * 2)


def main_ninja(options, args):
  """Interprets options, clobbers object files, and calls ninja."""

  # Prepare environment.
  env = EchoDict(os.environ)
  goma_ready = goma_setup(options, env)
  exit_status = -1
  try:
    if not goma_ready:
      assert options.compiler not in ('goma', 'goma-clang')
      assert options.goma_dir is None

    # ninja is different from all the other build systems in that it requires
    # most configuration to be done at gyp time. This is why this function does
    # less than the other comparable functions in this file.
    print 'chdir to %s' % options.src_dir
    os.chdir(options.src_dir)

    command = [options.ninja_path, '-w', 'dupbuild=err',
                                   '-C', options.target_output_dir]

    # HACK(yyanagisawa): update environment files on |env| update.
    # For compiling on Windows, environment in environment files are used.
    # It means even if enviroment such as GOMA_DISABLED is updated in
    # compile.py, the update will be ignored.
    # We need to update environment files to reflect the update.
    if chromium_utils.IsWindows() and NeedEnvFileUpdateOnWin(env):
      print 'Updating environment.{x86,x64} files.'
      UpdateWindowsEnvironment(options.target_output_dir, env)

    if options.clobber:
      print 'Removing %s' % options.target_output_dir
      # Deleting output_dir would also delete all the .ninja files necessary to
      # build. Clobbering should run before runhooks (which creates .ninja
      # files). For now, only delete all non-.ninja files.
      # TODO(thakis): Make "clobber" a step that runs before "runhooks".
      # Once the master has been restarted, remove all clobber handling
      # from compile.py, https://crbug.com/574557
      build_directory.RmtreeExceptNinjaOrGomaFiles(options.target_output_dir)

    if options.verbose:
      command.append('-v')
    command.extend(options.build_args)
    command.extend(args)

    maybe_set_official_build_envvars(options, env)

    if options.compiler:
      print 'using', options.compiler

    if options.compiler in ('goma', 'goma-clang'):
      assert options.goma_dir

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
        # For the safety, we'd like to set the upper limit to 200.
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
            ['slave%d-c1' % x for x in [20, 33] + range(78, 108)]):
          return min(10 * number_of_processors, 200)

        return 50

      goma_jobs = determine_goma_jobs()
      command.append('-j%d' % goma_jobs)

    # Run the build.
    env.print_overrides()
    exit_status = chromium_utils.RunCommand(command, env=env)
    if exit_status == 0 and options.ninja_ensure_up_to_date:
      # Run the build again if we want to check that the no-op build is clean.
      filter_obj = EnsureUpToDateFilter()
      # Append `-d explain` to help diagnose in the failure case.
      command += ['-d', 'explain']
      chromium_utils.RunCommand(command, env=env, filter_obj=filter_obj)
      if not filter_obj.was_up_to_date:
        print 'Failing build because ninja reported work to do.'
        print 'This means that after completing a compile, another was run and'
        print 'it resulted in still having work to do (that is, a no-op build'
        print 'wasn\'t a no-op). Consult the first "ninja explain:" line for a'
        print 'likely culprit.'
        return 1
    return exit_status
  finally:
    goma_teardown(options, env, exit_status)

    override_gsutil = None
    if options.gsutil_py_path:
      override_gsutil = [sys.executable, options.gsutil_py_path]

    goma_utils.UploadNinjaLog(
        options.target_output_dir, options.compiler, command, exit_status,
        override_gsutil=override_gsutil)


def get_target_build_dir(args, options):
  """Keep this function in sync with src/build/landmines.py"""
  assert options.build_tool in ['make', 'ninja']
  if chromium_utils.IsLinux() and options.cros_board:
    # When building ChromeOS's Simple Chrome workflow, the output directory
    # has a CROS board name suffix.
    outdir = 'out_%s' % (options.cros_board,)
  elif options.out_dir:
    outdir = options.out_dir
  else:
    outdir = 'out'
  return os.path.abspath(os.path.join(options.src_dir, outdir, options.target))


def real_main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--clobber', action='store_true', default=False,
                           help='delete the output directory before compiling')
  option_parser.add_option('--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('--solution', default=None,
                           help='name of solution/sub-project to build')
  option_parser.add_option('--project', default=None,
                           help='name of project to build')
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option('--src-dir', default=None,
                           help='path to the root of the source tree')
  option_parser.add_option('--mode', default='dev',
                           help='build mode (dev or official) controlling '
                                'environment variables set during build')
  option_parser.add_option('--build-tool', default=None,
                           help='specify build tool (make, ninja)')
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
  option_parser.add_option('--goma-deps-cache-dir',
                           help='specify goma deps cache directory')
  option_parser.add_option('--goma-hermetic', default='error',
                           help='Set goma hermetic mode')
  option_parser.add_option('--goma-enable-remote-link', default=None,
                           help='Enable goma remote link.')
  option_parser.add_option('--goma-enable-compiler-info-cache',
                           action='store_true',
                           help='Enable goma CompilerInfo cache')
  option_parser.add_option('--goma-store-local-run-output', default=None,
                           help='Store local run output to goma servers.')
  option_parser.add_option('--goma-fail-fast', action='store_true')
  option_parser.add_option('--goma-disable-local-fallback', action='store_true')
  option_parser.add_option('--goma-jsonstatus',
                           help='Specify a file to dump goma_ctl jsonstatus.')
  option_parser.add_option('--goma-service-account-json-file',
                           help='Specify a file containing goma service account'
                                ' credentials')
  option_parser.add_option('--verbose', action='store_true')
  option_parser.add_option('--gsutil-py-path',
                           help='Specify path to gsutil.py script.')
  option_parser.add_option('--ninja-path', default='ninja',
                           help='Specify path to the ninja tool.')
  option_parser.add_option('--ninja-ensure-up-to-date', action='store_true',
                           help='Checks the output of the ninja builder to '
                                'confirm that a second compile immediately '
                                'the first is a no-op.')

  options, args = option_parser.parse_args()

  if not options.src_dir:
    options.src_dir = 'src'
  options.src_dir = os.path.abspath(options.src_dir)

  options.build_dir = os.path.abspath(build_directory.GetBuildOutputDirectory(
        os.path.basename(options.src_dir)))

  if options.build_tool is None:
    if chromium_utils.IsWindows():
      main = main_ninja
      options.build_tool = 'ninja'
      # TODO(thakis): Remove the next two lines and merge this with the linux
      # branch below.
      if options.project:
        args += [options.project]
    elif chromium_utils.IsLinux() or chromium_utils.IsMac():
      main = main_ninja
      options.build_tool = 'ninja'
    else:
      print 'Please specify --build-tool.'
      return 1
  else:
    build_tool_map = {
        'make' : main_make,
        'ninja' : main_ninja,
    }
    main = build_tool_map.get(options.build_tool)
    if not main:
      sys.stderr.write('Unknown build tool %s.\n' % repr(options.build_tool))
      return 2

  options.target_output_dir = get_target_build_dir(args, options)

  return main(options, args)


if '__main__' == __name__:
  sys.exit(real_main())
