#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import codecs
import copy
import optparse
import os
import pprint
import shutil
import socket
import subprocess
import sys
import time
import urlparse

import os.path as path

from common import chromium_utils


RECOGNIZED_PATHS = {
    # If SVN path matches key, the entire URL is rewritten to the Git url.
    '/chrome/trunk/src':
        'https://chromium.googlesource.com/chromium/src.git',
    '/chrome-internal/trunk/src-internal':
        'https://chrome-internal.googlesource.com/chrome/src-internal.git'
}



BOT_UPDATE_MESSAGE = """
What is the "Bot Update" doing here?
====================================

The bot update step ensures that a checkout with the
proper revision and patchset is present on the bot.

You may be wondering - why is this step here if "gclient revert" and
"update" is on the bot already?  The reason is that we are preparing to
transition from SVN to Git.

Please pardon the dust while we fully convert everything to Git,
in the meantime we need this shim order to perform a gradual rollout.

master: %(master)s
builder: %(builder)s
slave: %(slave)s
bot_update.py is:"""

ACTIVATED_MESSAGE = """ACTIVE.
The bot will perform a Git checkout in this step.
The "gclient revert" and "update" steps are no-ops.

"""

NOT_ACTIVATED_MESSAGE = """INACTIVE.
This step does nothing. You actually want to look at the "update" step.

"""


GCLIENT_TEMPLATE = """solutions = %(solutions)s

cache_dir = %(cache_dir)s
"""

ENABLED_MASTERS = ['chromium.git']
ENABLED_BUILDERS = {}
ENABLED_SLAVES = {}

# Disabled filters get run AFTER enabled filters, so for example if a builder
# config is enabled, but a bot on that builder is disabled, that bot will
# be disabled.
DISABLED_BUILDERS = {}
DISABLED_SLAVES = {}

# How many times to retry failed subprocess calls.
RETRIES = 3

SCRIPTS_PATH = path.dirname(path.dirname(path.abspath(__file__)))
DEPS2GIT_DIR_PATH = path.join(SCRIPTS_PATH, 'tools', 'deps2git')
DEPS2GIT_PATH = path.join(DEPS2GIT_DIR_PATH, 'deps2git.py')
S2G_INTERNAL_FROM_PATH = path.join(SCRIPTS_PATH, 'tools', 'deps2git_internal',
                                   'svn_to_git_internal.py')
S2G_INTERNAL_DEST_PATH = path.join(DEPS2GIT_DIR_PATH, 'svn_to_git_internal.py')

# ../../cache_dir aka /b/build/slave/cache_dir
THIS_DIR = path.abspath(os.getcwd())
BUILDER_DIR = path.dirname(THIS_DIR)
SLAVE_DIR = path.dirname(BUILDER_DIR)
CACHE_DIR = path.join(SLAVE_DIR, 'cache_dir')


class SubprocessFailed(Exception):
  pass


def call(*args, **kwargs):
  """Interactive subprocess call."""
  kwargs['stdout'] = subprocess.PIPE
  kwargs['stderr'] = subprocess.STDOUT
  for attempt in xrange(RETRIES):
    attempt_msg = '(retry #%d)' % attempt if attempt else ''
    print '===Running %s%s===' % (' '.join(args), attempt_msg)
    start_time = time.time()
    proc = subprocess.Popen(args, **kwargs)
    # This is here because passing 'sys.stdout' into stdout for proc will
    # produce out of order output.
    while True:
      buf = proc.stdout.read(1)
      if not buf:
        break
      sys.stdout.write(buf)
    code = proc.wait()
    elapsed_time = ((time.time() - start_time) / 60.0)
    if not code:
      print '===Succeeded in %.1f mins===' % elapsed_time
      print
      return 0
    print '===Failed in %.1f mins===' % elapsed_time
    print

  raise SubprocessFailed('%s failed with code %d in %s after %d attempts.' %
                         (' '.join(args), code, os.getcwd(), RETRIES))


def get_gclient_spec(solutions):
  return GCLIENT_TEMPLATE % {
      'solutions': pprint.pformat(solutions, indent=4),
      'cache_dir': '"%s"' % CACHE_DIR
  }


def check_enabled(master, builder, slave):
  if master in ENABLED_MASTERS:
    return True
  builder_list = ENABLED_BUILDERS.get(master)
  if builder_list and builder in builder_list:
    return True
  slave_list = ENABLED_SLAVES.get(master)
  if slave_list and slave in slave_list:
    return True
  return False


def check_disabled(master, builder, slave):
  """Returns True if disabled, False if not disabled."""
  builder_list = DISABLED_BUILDERS.get(master)
  if builder_list and builder in builder_list:
    return True
  slave_list = DISABLED_SLAVES.get(master)
  if slave_list and slave in slave_list:
    return True
  return False


def check_valid_host(master, builder, slave):
  return (check_enabled(master, builder, slave)
          and not check_disabled(master, builder, slave))


def solutions_printer(solutions):
  """Prints gclient solution to stdout."""
  print 'Gclient Solutions'
  print '================='
  for solution in solutions:
    name = solution.get('name')
    url = solution.get('url')
    print '%s (%s)' % (name, url)
    if solution.get('deps_file'):
      print '  Dependencies file is %s' % solution['deps_file']
    if 'managed' in solution:
      print '  Managed mode is %s' % ('ON' if solution['managed'] else 'OFF')
    custom_vars = solution.get('custom_vars')
    if custom_vars:
      print '  Custom Variables:'
      for var_name, var_value in sorted(custom_vars.iteritems()):
        print '    %s = %s' % (var_name, var_value)
    custom_deps = solution.get('custom_deps')
    if 'custom_deps' in solution:
      print '  Custom Dependencies:'
      for deps_name, deps_value in sorted(custom_deps.iteritems()):
        if deps_value:
          print '    %s -> %s' % (deps_name, deps_value)
        else:
          print '    %s: Ignore' % deps_name
    print


def solutions_to_git(input_solutions):
  """Modifies urls in solutions to point at Git repos."""
  solutions = copy.deepcopy(input_solutions)
  for solution in solutions:
    original_url = solution['url']
    parsed_url = urlparse.urlparse(original_url)
    parsed_path = parsed_url.path
    if parsed_path in RECOGNIZED_PATHS:
      solution['url'] = RECOGNIZED_PATHS[parsed_path]
    else:
      print 'Warning: path %s not recognized' % parsed_path
    if solution.get('deps_file', 'DEPS') == 'DEPS':
      solution['deps_file'] = '.DEPS.git'
    solution['managed'] = False
  return solutions


def ensure_no_checkout(dir_names, scm_dirname):
  """Ensure that there is no git checkout under build/.

  If there is an incorrect checkout under build/, then
  move build/ to build.dead/
  This function will check each directory in dir_names.

  scm_dirname is expected to be either ['.svn', '.git']
  """
  assert scm_dirname in ['.svn', '.git']
  has_checkout = any(map(lambda dir_name: path.exists(
      path.join(os.getcwd(), dir_name, scm_dirname)), dir_names))

  if has_checkout:
    # cd .. && rm -rf ./build && mkdir ./build && cd build
    build_dir = os.getcwd()

    os.chdir(path.dirname(os.getcwd()))
    print '%s detected in checkout, deleting %s...' % (scm_dirname, build_dir),
    chromium_utils.RemoveDirectory(build_dir)
    print 'done'
    os.mkdir(build_dir)
    os.chdir(build_dir)



def gclient_configure(solutions):
  """Should do the same thing as gclient --spec='...'."""
  with codecs.open('.gclient', mode='w', encoding='utf-8') as f:
    f.write(get_gclient_spec(solutions))


def gclient_sync():
  call('gclient', 'sync', '--verbose', '--reset', '--force',
       '--nohooks', '--noprehooks')


def get_git_hash(revision, dir_name):
  match = "^git-svn-id: [^ ]*@%d" % revision
  cmd = ['git', 'log', '--grep', match, '--format=%H', dir_name]
  return subprocess.check_output(cmd).strip() or None


def deps2git(sln_dirs):
  for sln_dir in sln_dirs:
    deps_file = path.join(os.getcwd(), sln_dir, 'DEPS')
    deps_git_file = path.join(os.getcwd(), sln_dir, '.DEPS.git')
    if not path.isfile(deps_file):
      return
    # Do we have a better way of doing this....?
    repo_type = 'internal' if 'internal' in sln_dir else 'public'
    # TODO(hinoka): This will be what populates the git caches on the first
    #               run for all of the bots.  Since deps2git is single threaded,
    #               all of this will run in a single threaded context and be
    #               super slow.  Should make deps2git multithreaded.
    call(sys.executable, DEPS2GIT_PATH, '-t', repo_type,
         '--cache_dir=%s' % CACHE_DIR,
         '--deps=%s' % deps_file, '--out=%s' % deps_git_file)


def git_checkout(solutions, revision):
  build_dir = os.getcwd()
  # Revision only applies to the first solution.
  first_solution = True
  for sln in solutions:
    name = sln['name']
    url = sln['url']
    sln_dir = path.join(build_dir, name)
    if not path.isdir(sln_dir):
      call('git', 'clone', url, sln_dir)

    # Clean out .DEPS.git changes first.
    call('git', 'reset', '--hard', cwd=sln_dir)
    call('git', 'clean', '-df', cwd=sln_dir)
    call('git', 'pull', 'origin', 'master', cwd=sln_dir)
    # TODO(hinoka): We probably have to make use of revision mapping.
    if first_solution and revision and revision.lower() != 'head':
      if revision and revision.isdigit() and len(revision) < 40:
        # rev_num is really a svn revision number, convert it into a git hash.
        git_ref = get_git_hash(revision, name)
      else:
        # rev_num is actually a git hash or ref, we can just use it.
        git_ref = revision
      call('git', 'checkout', git_ref, cwd=sln_dir)
    else:
      call('git', 'checkout', 'origin/master', cwd=sln_dir)

    first_solution = False


def apply_issue(issue, patchset, root, server):
  pass


def delete_flag(flag_file):
  """Remove bot update flag."""
  if os.path.exists(flag_file):
    os.remove(flag_file)


def emit_flag(flag_file):
  """Deposit a bot update flag on the system to tell gclient not to run."""
  print 'Emitting flag file at %s' % flag_file
  with open(flag_file, 'wb') as f:
    f.write('Success!')


def parse_args():
  parse = optparse.OptionParser()

  parse.add_option('--issue', help='Issue number to patch from.')
  parse.add_option('--patchset',
                   help='Patchset from issue to patch from, if applicable.')
  parse.add_option('--patch_url', help='Optional URL to SVN patch.')
  parse.add_option('--root', help='Repository root.')
  parse.add_option('--rietveld_server', help='Rietveld server.')
  parse.add_option('--specs', help='Gcilent spec.')
  parse.add_option('--master', help='Master name.')
  parse.add_option('-f', '--force', action='store_true',
                   help='Bypass check to see if we want to be run. '
                        'Should ONLY be used locally.')
  # TODO(hinoka): We don't actually use this yet, we should factor this in.
  parse.add_option('--revision-mapping')
  parse.add_option('--revision')
  parse.add_option('--slave_name', default=socket.getfqdn().split('.')[0],
                   help='Hostname of the current machine, '
                   'used for determining whether or not to activate.')
  parse.add_option('--builder_name', help='Name of the builder, '
                   'used for determining whether or not to activate.')
  parse.add_option('--build_dir', default=os.getcwd())
  parse.add_option('--flag_file', default=path.join(os.getcwd(),
                                                          'update.flag'))

  return parse.parse_args()


def main():
  # Get inputs.
  options, _ = parse_args()
  builder = options.builder_name
  slave = options.slave_name
  master = options.master

  # Check if this script should activate or not.
  active = check_valid_host(master, builder, slave) or options.force

  # Print helpful messages to tell devs whats going on.
  print BOT_UPDATE_MESSAGE % {
    'master': master,
    'builder': builder,
    'slave': slave,
  },
  # Print to stderr so that it shows up red on win/mac.
  print ACTIVATED_MESSAGE if active else NOT_ACTIVATED_MESSAGE

  # Parse, munipulate, and print the gclient solutions.
  specs = {}
  exec(options.specs, specs)
  svn_solutions = specs.get('solutions', [])
  git_solutions = solutions_to_git(svn_solutions)
  solutions_printer(git_solutions)

  # Cleanup svn checkout if active, otherwise remove git checkout and exit.
  dir_names = [sln.get('name') for sln in svn_solutions if 'name' in sln]
  if active:
    ensure_no_checkout(dir_names, '.svn')
    emit_flag(options.flag_file)
  else:
    ensure_no_checkout(dir_names, '.git')
    delete_flag(options.flag_file)
    return

  # Get a checkout of each solution, without DEPS or hooks.
  # Calling git directory because there is no way to run Gclient without
  # invoking DEPS.
  print 'Fetching Git checkout'
  git_checkout(git_solutions, options.revision)

  # TODO(hinoka): This must be implemented before we can turn this on for TS.
  # if options.issue:
  #   apply_issue(options.issue, options.patchset, options.root, options.server)

  # Magic to get deps2git to work with internal DEPS.
  shutil.copyfile(S2G_INTERNAL_FROM_PATH, S2G_INTERNAL_DEST_PATH)
  deps2git(dir_names)

  gclient_configure(git_solutions)
  gclient_sync()


if __name__ == '__main__':
  sys.exit(main())
