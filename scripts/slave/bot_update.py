#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import codecs
import copy
import cStringIO
import ctypes
import json
import optparse
import os
import pprint
import shutil
import socket
import subprocess
import sys
import time
import urllib2
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
What is the "Bot Update" step?
==============================

This step ensures that the source checkout on the bot (e.g. Chromium's src/ and
its dependencies) is checked out in a consistent state. This means that all of
the necessary repositories are checked out, no extra repositories are checked
out, and no locally modified files are present.

These actions used to be taken care of by the "gclient revert" and "update"
steps. However, those steps are known to be buggy and occasionally flaky. This
step has two main advantages over them:
  * it only operates in Git, so the logic can be clearer and cleaner; and
  * it is a slave-side script, so its behavior can be modified without
    restarting the master.

Why Git, you ask? Because that is the direction that the Chromium project is
heading. This step is an integral part of the transition from using the SVN repo
at chrome/trunk/src to using the Git repo src.git. Please pardon the dust while
we fully convert everything to Git. This message will get out of your way
eventually, and the waterfall will be a happier place because of it.

This step can be activated or deactivated independently on every builder on
every master. When it is active, the "gclient revert" and "update" steps become
no-ops. When it is inactive, it prints this message, cleans up after itself, and
lets everything else continue as though nothing has changed. Eventually, when
everything is stable enough, this step will replace them entirely.

Debugging information:
(master/builder/slave may be unspecified on recipes)
master: %(master)s
builder: %(builder)s
slave: %(slave)s
forced by recipes: %(recipe)s
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

# IMPORTANT: If you're trying to enable a RECIPE bot, you'll need to
# edit recipe_modules/bot_update/api.py instead.
ENABLED_MASTERS = ['chromium.git']
ENABLED_BUILDERS = {
    'tryserver.chromium': ['linux_rel_alt'],
}
ENABLED_SLAVES = {
    # This is enabled on a bot-to-bot basis to ensure that we don't have
    # bots that have mixed configs.
    'chromium.fyi': [
        'build1-m1',  # Chromium Builder / Chromium Builder (dbg)
        'vm928-m1',   # Chromium Linux Buildrunner
        'vm859-m1',   # Chromium Linux Redux
        'vm933-m1',   # ChromiumOS Linux Tests
    ]
}

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
# Because we print CACHE_DIR out into a .gclient file, and then later run
# eval() on it, backslashes need to be escaped, otherwise "E:\b\build" gets
# parsed as "E:[\x08][\x08]uild".
if sys.platform.startswith('win'):
  CACHE_DIR = CACHE_DIR.replace('\\', '\\\\')

# Find the patch tool.
ROOT_BUILD_DIR = path.dirname(SLAVE_DIR)
ROOT_B_DIR = path.dirname(ROOT_BUILD_DIR)
BUILD_INTERNAL_DIR = path.join(ROOT_B_DIR, 'build_internal')
if sys.platform.startswith('win'):
  PATCH_TOOL = path.join(BUILD_INTERNAL_DIR, 'tools', 'patch.EXE')
else:
  PATCH_TOOL = '/usr/bin/patch'

# If there is less than 100GB of disk space on the system, then we do
# a shallow checkout.
SHALLOW_CLONE_THRESHOLD = 100 * 1024 * 1024 * 1024


class SubprocessFailed(Exception):
  def __init__(self, message, code):
    Exception.__init__(self, message)
    self.code = code


def call(*args, **kwargs):
  """Interactive subprocess call."""
  kwargs['stdout'] = subprocess.PIPE
  kwargs['stderr'] = subprocess.STDOUT
  stdin_data = kwargs.pop('stdin_data', None)
  if stdin_data:
    kwargs['stdin'] = subprocess.PIPE
  out = cStringIO.StringIO()
  for attempt in xrange(RETRIES):
    attempt_msg = ' (retry #%d)' % attempt if attempt else ''
    print '===Running %s%s===' % (' '.join(args), attempt_msg)
    start_time = time.time()
    proc = subprocess.Popen(args, **kwargs)
    if stdin_data:
      proc.stdin.write(stdin_data)
      proc.stdin.close()
    # This is here because passing 'sys.stdout' into stdout for proc will
    # produce out of order output.
    while True:
      buf = proc.stdout.read(1)
      if buf == '\r' and not sys.platform.startswith('win'):
        # We want to make sure the git status message, which are normally
        # printed with just a carriage return (\r) without the newline (\n)
        # are printed with newlines instead.
        # However, on Windows all the newlines are \r\n, so this ends up
        # double spacing the lines.
        buf = '\n'
      if not buf:
        break
      sys.stdout.write(buf)
      out.write(buf)
    code = proc.wait()
    elapsed_time = ((time.time() - start_time) / 60.0)
    if not code:
      print '===Succeeded in %.1f mins===' % elapsed_time
      print
      return out.getvalue()
    print '===Failed in %.1f mins===' % elapsed_time
    print

  raise SubprocessFailed('%s failed with code %d in %s after %d attempts.' %
                         (' '.join(args), code, os.getcwd(), RETRIES), code)


def git(*args, **kwargs):
  """Wrapper around call specifically for Git commands."""
  git_executable = 'git'
  # On windows, subprocess doesn't fuzzy-match 'git' to 'git.bat', so we
  # have to do it explicitly. This is better than passing shell=True.
  if sys.platform.startswith('win'):
    git_executable += '.bat'
  cmd = (git_executable,) + args
  return call(*cmd, **kwargs)


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
  """Ensure that there is no undesired checkout under build/.

  If there is an incorrect checkout under build/, then
  move build/ to build.dead/
  This function will check each directory in dir_names.

  scm_dirname is expected to be either ['.svn', '.git']
  """
  assert scm_dirname in ['.svn', '.git', '*']
  has_checkout = any(map(lambda dir_name: path.exists(
      path.join(os.getcwd(), dir_name, scm_dirname)), dir_names))

  if has_checkout or scm_dirname == '*':
    build_dir = os.getcwd()
    prefix = ''
    if scm_dirname != '*':
      prefix = '%s detected in checkout, ' % scm_dirname

    for filename in os.listdir(build_dir):
      deletion_target = path.join(build_dir, filename)
      print '%sdeleting %s...' % (prefix, deletion_target),
      if path.isdir(deletion_target):
        chromium_utils.RemoveDirectory(deletion_target)
      else:
        chromium_utils.RemoveFile(deletion_target)
      print 'done'


def gclient_configure(solutions):
  """Should do the same thing as gclient --spec='...'."""
  with codecs.open('.gclient', mode='w', encoding='utf-8') as f:
    f.write(get_gclient_spec(solutions))


def gclient_sync():
  gclient_bin = 'gclient.bat' if sys.platform.startswith('win') else 'gclient'
  call(gclient_bin, 'sync', '--verbose', '--reset', '--force',
       '--nohooks', '--noprehooks')


def create_less_than_or_equal_regex(number):
  """ Return a regular expression to test whether an integer less than or equal
      to 'number' is present in a given string.
  """

  # In three parts, build a regular expression that match any numbers smaller
  # than 'number'.
  # For example, 78656 would give a regular expression that looks like:
  # Part 1
  # (78356|            # 78356
  # Part 2
  #  7835[0-5]|        # 78350-78355
  #  783[0-4][0-9]|    # 78300-78349
  #  78[0-2][0-9]{2}|  # 78000-78299
  #  7[0-7][0-9]{3}|   # 70000-77999
  #  [0-6][0-9]{4}|    # 10000-69999
  # Part 3
  #  [0-9]{1,4}        # 0-9999

  # Part 1: Create an array with all the regexes, as described above.
  # Prepopulate it with the number itself.
  number = str(number)
  expressions = [number]

  # Convert the number to a list, so we can translate digits in it to
  # expressions.
  num_list = list(number)
  num_len = len(num_list)

  # Part 2: Go through all the digits in the number, starting from the end.
  # Each iteration appends a line to 'expressions'.
  for index in range (num_len - 1, -1, -1):
    # Convert this digit back to an integer.
    digit = int(num_list[index])

    # Part 2.1: No processing if this digit is a zero.
    if digit == 0:
      continue

    # Part 2.2: We switch the current digit X by a range "[0-(X-1)]".
    if digit == 1:
      num_list[index] = '0'
    else:
      num_list[index] = '[0-%d]' % (digit - 1)

    # Part 2.3: We set all following digits to be "[0-9]".
    # Since we just decrementented a digit in a most important position, all
    # following digits don't matter. The possible numbers will always be smaller
    # than before we decremented.
    if (index + 1) < num_len:
      if (num_len - (index + 1)) == 1:
        num_list[index + 1] = '[0-9]'
      else:
        num_list[index + 1] = '[0-9]{%s}' % (num_len - (index + 1))

    # Part 2.4: Add this new sub-expression to the list.
    expressions.append(''.join(num_list[:min(index+2, num_len)]))

  # Part 3: We add all the full ranges to match all numbers that are at least
  # one order of magnitude smaller than the original numbers.
  if num_len == 2:
    expressions.append('[0-9]')
  elif num_len > 2:
    expressions.append('[0-9]{1,%s}' % (num_len - 1))

  # All done. We now have our final regular expression.
  regex = '(%s)' % ('|'.join(expressions))
  return regex


def get_git_hash(revision, dir_name):
  match = "^git-svn-id: [^ ]*@%s " % create_less_than_or_equal_regex(revision)
  cmd = ['log', '-E', '--grep', match, '--format=%H', '--max-count=1']
  results = git(*cmd, cwd=dir_name).strip().splitlines()
  if results:
    return results[0]
  raise Exception('We can\'t resolve svn revision %s into a git hash' %
                  revision)


def _last_commit_for_file(filename, repo_base):
  cmd = ['log', '--format=%H', '--max-count=1', '--', filename]
  return git(*cmd, cwd=repo_base).strip()


def need_to_run_deps2git(repo_base, deps_file, deps_git_file):
  """Checks to see if we need to run deps2git.

  Returns True if there was a DEPS change after the last .DEPS.git update.
  """
  if not path.isfile(deps_git_file):
    # .DEPS.git doesn't exist but DEPS does? We probably want to generate one.
    return True

  last_known_deps_ref = _last_commit_for_file(deps_file, repo_base)
  last_known_deps_git_ref = _last_commit_for_file(deps_git_file, repo_base)
  merge_base_ref = git('merge-base', last_known_deps_ref,
                       last_known_deps_git_ref, cwd=repo_base).strip()

  # If the merge base of the last DEPS and last .DEPS.git file is not
  # equivilent to the hash of the last DEPS file, that means the DEPS file
  # was committed after the last .DEPS.git file.
  return last_known_deps_ref != merge_base_ref


def ensure_deps2git(sln_dir, shallow):
  repo_base = path.join(os.getcwd(), sln_dir)
  deps_file = path.join(repo_base, 'DEPS')
  deps_git_file = path.join(repo_base, '.DEPS.git')
  if not path.isfile(deps_file):
    return

  if not need_to_run_deps2git(repo_base, deps_file, deps_git_file):
    return

  print '===DEPS file modified, need to run deps2git==='
  # Magic to get deps2git to work with internal DEPS.
  shutil.copyfile(S2G_INTERNAL_FROM_PATH, S2G_INTERNAL_DEST_PATH)

  # TODO(hinoka): This might need to be smarter if we need to deal with
  #               DEPS changes that are in an internal repository.
  repo_type = 'internal' if 'internal' in sln_dir else 'public'
  cmd = [sys.executable, DEPS2GIT_PATH,
         '-t', repo_type,
         '--cache_dir=%s' % CACHE_DIR,
         '--deps=%s' % deps_file,
         '--out=%s' % deps_git_file]
  if shallow:
    cmd.append('--shallow')
  call(*cmd)


def emit_got_revision(revision):
  print '@@@SET_BUILD_PROPERTY@got_revision@"%s"@@@' % revision


# Derived from:
# http://code.activestate.com/recipes/577972-disk-usage/?in=user-4178764
def get_total_disk_space():
  cwd = os.getcwd()
  # Windows is the only platform that doesn't support os.statvfs, so
  # we need to special case this.
  if sys.platform.startswith('win'):
    _, total, free = (ctypes.c_ulonglong(), ctypes.c_ulonglong(), \
                      ctypes.c_ulonglong())
    if sys.version_info >= (3,) or isinstance(cwd, unicode):
      fn = ctypes.windll.kernel32.GetDiskFreeSpaceExW
    else:
      fn = ctypes.windll.kernel32.GetDiskFreeSpaceExA
    ret = fn(cwd, ctypes.byref(_), ctypes.byref(total), ctypes.byref(free))
    if ret == 0:
      # WinError() will fetch the last error code.
      raise ctypes.WinError()
    return (total.value, free.value)

  else:
    st = os.statvfs(cwd)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    return (total, free)


def git_checkout(solutions, revision, shallow, sub_annotations):
  build_dir = os.getcwd()
  # Before we do anything, break all git_cache locks.
  if path.isdir(CACHE_DIR):
    git('cache', 'unlock', '-vv', '--force', '--all', '--cache-dir', CACHE_DIR)
    for item in os.listdir(CACHE_DIR):
      filename = os.path.join(CACHE_DIR, item)
      if item.endswith('.lock'):
        raise Exception('%s exists after cache unlock' % filename)
  # Revision only applies to the first solution.
  first_solution = True
  for sln in solutions:
    name = sln['name']
    url = sln['url']
    sln_dir = path.join(build_dir, name)
    s = ['--shallow'] if shallow else []
    populate_cmd = (['cache', 'populate', '-v', '--cache-dir', CACHE_DIR]
                 + s + [url])
    git(*populate_cmd)
    mirror_dir = git('cache', 'exists', '--cache-dir', CACHE_DIR, url).strip()
    if not path.isdir(sln_dir):
      git('clone', mirror_dir, sln_dir)
    try:
      # Make sure we start on a known branch first, and not where ever
      # apply_issue left us at before.
      git('checkout', '--force', 'origin/master', cwd=sln_dir)
      git('reset', '--hard', cwd=sln_dir)
    except SubprocessFailed as e:
      if e.code == 128:
        # Exited abnormally, theres probably something wrong with the checkout.
        # Lets wipe the checkout and try again.
        chromium_utils.RemoveDirectory(sln_dir)
        git('clone', mirror_dir, sln_dir)
        git('checkout', '--force', 'origin/master', cwd=sln_dir)
        git('reset', '--hard', cwd=sln_dir)
      else:
        raise

    git('clean', '-df', cwd=sln_dir)
    git('pull', 'origin', 'master', cwd=sln_dir)
    # TODO(hinoka): We probably have to make use of revision mapping.
    if first_solution and revision and revision.lower() != 'head':
      if sub_annotations:
        emit_got_revision(revision)
      if revision and revision.isdigit() and len(revision) < 40:
        # rev_num is really a svn revision number, convert it into a git hash.
        git_ref = get_git_hash(int(revision), name)
      else:
        # rev_num is actually a git hash or ref, we can just use it.
        git_ref = revision
      git('checkout', git_ref, cwd=sln_dir)
    else:
      git('checkout', 'origin/master', cwd=sln_dir)
      if first_solution:
        git_ref = git('log', '--format=%H', '--max-count=1',
                      cwd=sln_dir).strip()

    first_solution = False
  return git_ref


def _download(url):
  """Fetch url and return content, with retries for flake."""
  for attempt in xrange(RETRIES):
    try:
      return urllib2.urlopen(url).read()
    except Exception:
      if attempt == RETRIES - 1:
        raise


def apply_issue_svn(root, patch_url):
  patch_data = call('svn', 'cat', patch_url)
  call(PATCH_TOOL, '-p0', '--remove-empty-files', '--force', '--forward',
       stdin_data=patch_data, cwd=root)


def apply_issue_rietveld(issue, patchset, root, server, rev_map, revision):
  apply_issue_bin = ('apply_issue.bat' if sys.platform.startswith('win')
                     else 'apply_issue')
  rev_map = json.loads(rev_map)
  if root in rev_map and rev_map[root] == 'got_revision':
    rev_map[root] = revision
  call(apply_issue_bin,
       '--root_dir', root,
       '--issue', issue,
       '--patchset', patchset,
       '--no-auth',
       '--server', server,
       '--revision-mapping', json.dumps(rev_map),
       '--base_ref', revision,
       '--force')


def check_flag(flag_file):
  """Returns True if the flag file is present."""
  return os.path.isfile(flag_file)


def delete_flag(flag_file):
  """Remove bot update flag."""
  if os.path.isfile(flag_file):
    os.remove(flag_file)


def emit_flag(flag_file):
  """Deposit a bot update flag on the system to tell gclient not to run."""
  print 'Emitting flag file at %s' % flag_file
  with open(flag_file, 'wb') as f:
    f.write('Success!')


def ensure_emit_json(out_file, did_run, **kwargs):
  """Write run information into a JSON file."""
  if out_file:
    output = {'did_run': did_run}
    output.update(kwargs)
    with open(out_file, 'wb') as f:
      f.write(json.dumps(output))


def parse_args():
  parse = optparse.OptionParser()

  parse.add_option('--issue', help='Issue number to patch from.')
  parse.add_option('--patchset',
                   help='Patchset from issue to patch from, if applicable.')
  parse.add_option('--patch_url', help='Optional URL to SVN patch.')
  parse.add_option('--root', help='Repository root.')
  parse.add_option('--rietveld_server',
                   default='codereview.chromium.org',
                   help='Rietveld server.')
  parse.add_option('--specs', help='Gcilent spec.')
  parse.add_option('--master', help='Master name.')
  parse.add_option('-f', '--force', action='store_true',
                   help='Bypass check to see if we want to be run. '
                        'Should ONLY be used locally.')
  parse.add_option('--revision_mapping')
  parse.add_option('--revision-mapping')  # Backwards compatability.
  parse.add_option('--revision')
  parse.add_option('--slave_name', default=socket.getfqdn().split('.')[0],
                   help='Hostname of the current machine, '
                   'used for determining whether or not to activate.')
  parse.add_option('--builder_name', help='Name of the builder, '
                   'used for determining whether or not to activate.')
  parse.add_option('--build_dir', default=os.getcwd())
  parse.add_option('--flag_file', default=path.join(os.getcwd(),
                                                    'update.flag'))
  parse.add_option('--shallow', action='store_true',
                   help='Use shallow clones for cache repositories.')
  parse.add_option('-o', '--output_json',
                   help='Output JSON information into a specified file')


  return parse.parse_args()


def main():
  # Get inputs.
  options, _ = parse_args()
  builder = options.builder_name
  slave = options.slave_name
  master = options.master

  # Check if this script should activate or not.
  active = check_valid_host(master, builder, slave) or options.force or False

  # Print helpful messages to tell devs whats going on.
  if options.force and options.output_json:
    recipe_force = 'Forced on by recipes'
  elif active and options.output_json:
    recipe_force = 'Off by recipes, but forced on by bot update'
  elif not active and options.output_json:
    recipe_force = 'Forced off by recipes'
  else:
    recipe_force = 'N/A. Was not called by recipes'

  print BOT_UPDATE_MESSAGE % {
    'master': master or 'Not specified',
    'builder': builder or 'Not specified',
    'slave': slave or 'Not specified',
    'recipe': recipe_force,
  },
  # Print to stderr so that it shows up red on win/mac.
  print ACTIVATED_MESSAGE if active else NOT_ACTIVATED_MESSAGE

  # Parse, munipulate, and print the gclient solutions.
  specs = {}
  exec(options.specs, specs)
  svn_solutions = specs.get('solutions', [])
  git_solutions = solutions_to_git(svn_solutions)
  solutions_printer(git_solutions)

  dir_names = [sln.get('name') for sln in svn_solutions if 'name' in sln]
  # If we're active now, but the flag file doesn't exist (we weren't active last
  # run) or vice versa, blow away all checkouts.
  if bool(active) != bool(check_flag(options.flag_file)):
    ensure_no_checkout(dir_names, '*')
  ensure_emit_json(options.output_json, did_run=active)
  if active:
    ensure_no_checkout(dir_names, '.svn')
    emit_flag(options.flag_file)
  else:
    delete_flag(options.flag_file)
    return

  # Do a shallow checkout if the disk is less than 100GB.
  total_disk_space, free_disk_space = get_total_disk_space()
  total_disk_space_gb = int(total_disk_space / (1024 * 1024 * 1024))
  used_disk_space_gb = int((total_disk_space - free_disk_space)
                           / (1024 * 1024 * 1024))
  percent_used = int(used_disk_space_gb * 100 / total_disk_space_gb)
  step_text = '[%dGB/%dGB used (%d%%)]' % (used_disk_space_gb,
                                           total_disk_space_gb,
                                           percent_used)
  if not options.output_json:
    print '@@@STEP_TEXT@%s@@@' % step_text
  if not options.shallow:
    options.shallow = total_disk_space < SHALLOW_CLONE_THRESHOLD

  # Get a checkout of each solution, without DEPS or hooks.
  # Calling git directory because there is no way to run Gclient without
  # invoking DEPS.
  print 'Fetching Git checkout'
  got_revision = git_checkout(git_solutions, options.revision, options.shallow,
                              options.output_json is None)

  options.root =  options.root or dir_names[0]
  if options.patch_url:
    apply_issue_svn(options.root, options.patch_url)
  elif options.issue:
    apply_issue_rietveld(options.issue, options.patchset, options.root,
                         options.rietveld_server, options.revision_mapping,
                         got_revision)

  # Run deps2git if there is a DEPS commit after the last .DEPS.git commit.
  ensure_deps2git(options.root, options.shallow)

  gclient_configure(git_solutions)
  gclient_sync()

  # Tell recipes information such as root, got_revision, etc.
  properties = {
      'got_revision': got_revision
  }
  ensure_emit_json(options.output_json,
                   did_run=True,
                   root=options.root,
                   step_text=step_text,
                   properties=properties)


if __name__ == '__main__':
  sys.exit(main())
