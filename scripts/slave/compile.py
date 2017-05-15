#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to build chrome, executed by buildbot.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

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
  option_parser.add_option('--goma-enable-localoutputcache', default=None,
                           help='Enable goma LocalOutputCache.')
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
  option_parser.add_option(
      '--cloudtail-service-account-json', default=None,
      help='Specify a file for cloudtail service account json path.')

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
  goma_ready, goma_cloudtail = goma_utils.Setup(options, env)

  if not goma_ready:
    assert options.compiler not in ('goma', 'goma-clang')
    assert options.goma_dir is None
  elif options.goma_jobs is None:
    options.goma_jobs = goma_utils.DetermineGomaJobs()

  # build
  exit_status = main_ninja(options, args, env)

  # stop goma
  goma_utils.Teardown(options, env, exit_status, goma_cloudtail)

  return exit_status


if '__main__' == __name__:
  sys.exit(real_main())
