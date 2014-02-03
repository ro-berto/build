#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import copy
import optparse
import os
import sys
import urlparse


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

ENABLED_MASTERS = ['chromium.git']
# Master: Builders dict.
ENABLED_BUILDERS = {}
# Master: Slaves dict.
ENABLED_SLAVES = {}

# Disabled filters get run AFTER enabled filters, so for example if a builder
# config is enabled, but a bot on that builder is disabled, that bot will
# be disabled.
DISABLED_BUILDERS = {}
DISABLED_SLAVES = {}


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
  return False


def solutions_printer(solutions):
  """Prints gclient solution to stdout."""
  print 'Gclient Solutions'
  print '================='
  for solution in solutions:
    name = solution.get('name')
    url = solution.get('url')
    print '%s (%s)' % (name, url)
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
    if solution.get('deps_file'):
      print '  Dependencies file is %s' % solution['deps_file']
    if 'managed' in solution:
      print '  Managed mode is %s' % ('ON' if solution['managed'] else 'OFF')
    print


def solutions_to_git(input_solutions):
  """Modifies urls in solutions to point at Git repos."""
  solutions = copy.deepcopy(input_solutions)
  for solution in solutions:
    original_url = solution['url']
    parsed_url = urlparse.urlparse(original_url)
    path = parsed_url.path
    if path in RECOGNIZED_PATHS:
      solution['url'] = RECOGNIZED_PATHS[path]
    else:
      print 'Warning: path %s not recognized' % path
    if solution.get('deps_file', 'DEPS') == 'DEPS':
      solution['deps_file'] = '.DEPS.git'
    solution['managed'] = False
  return solutions


def ensure_no_git_checkout():
  """Ensure that there is no git checkout under build/.

  If there is a git checkout under build/, then move build/ to build.dead/
  """
  pass


def ensure_no_svn_checkout():
  """Ensure that there is no svn checkout under build/.

  If there is a svn checkout under build/, then move build/ to build.dead/
  """
  pass


def gclient_configure(solutions):
  pass


def gclient_shallow_sync():
  pass


def git_pull_and_clean():
  pass


def apply_issue(issue, patchset, root, server):
  pass


def deps2git():
  pass


def gclient_sync():
  pass


def deposit_bot_update_flag():
  """Deposit a bot update flag on the system to tell gclient not to run."""
  pass


def parse_args():
  parse = optparse.OptionParser()

  parse.add_option('-i', '--issue', help='Issue number to patch from.')
  parse.add_option('-p', '--patchset',
                   help='Patchset from issue to patch from, if applicable.')
  parse.add_option('-r', '--root', help='Repository root.')
  parse.add_option('-c', '--server', help='Rietveld server.')
  parse.add_option('-s', '--specs', help='Gcilent spec.')
  parse.add_option('-m', '--master', help='Master name.')
  parse.add_option('-f', '--force', action='store_true',
                   help='Bypass check to see if we want to be run. '
                        'Should ONLY be used locally.')
  parse.add_option('-e', '--revision-mapping')

  return parse.parse_args()


def main():
  # Get inputs.
  options, _ = parse_args()
  builder = os.environ.get('BUILDBOT_BUILDERNAME', None)
  slave = os.environ.get('BUILDBOT_SLAVENAME', None)
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
  exec(options.specs, specs)  # TODO(hinoka): LOL this is terrible.
  solutions = specs.get('solutions', [])
  git_solutions = solutions_to_git(solutions)
  solutions_printer(git_solutions)

  # Do the checkout.
  # TODO(hinoka): Uncomment these once they're implemented.
  # ensure_no_svn_checkout()
  # gclient_configure(git_solutions)
  # gclient_shallow_sync()
  # git_pull_and_clean()
  # if options.issue:
  #   apply_issue(options.issue, options.patchset, options.root, options.server)
  # deps2git()
  # gclient_sync()


if __name__ == '__main__':
  sys.exit(main())