#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
import urllib2


SLAVE_GCLIENT_CONFIG = """solutions = [
  {
    "name"      : "slave.DEPS",
    "url"       : "https://chrome-internal.googlesource.com/chrome/tools/build/slave.DEPS.git",
    "deps_file" : ".DEPS.git",
    "managed"   : True,
  },
]"""

INTERNAL_GCLIENT_CONFIG = """solutions = [
  {
    "name"      : "internal.DEPS",
    "url"       : "https://chrome-internal.googlesource.com/chrome/tools/build/internal.DEPS.git",
    "deps_file" : ".DEPS.git",
    "managed"   : True,
  },
]"""

GCLIENT_CONFIGS = {
  'slave.DEPS': SLAVE_GCLIENT_CONFIG,
  'internal.DEPS': INTERNAL_GCLIENT_CONFIG,
}

PREVENT_REBOOT_FILE_CONTENT = 'slave_svn_to_git'

is_win = sys.platform.startswith('win')


def check_call(cmd, cwd=None, env=None):
  print 'Running %s%s' % (cmd, ' in %s' % cwd if cwd else '')
  subprocess.check_call(cmd, cwd=cwd, shell=is_win, env=env)


def check_output(cmd, cwd=None, env=None):
  print 'Running %s%s' % (cmd, ' in %s' % cwd if cwd else '')
  return subprocess.check_output(cmd, cwd=cwd, shell=is_win, env=env)


def report_host_state(b_dir, cur_host):
  """Report host state to the tracking app.

  Args:
    b_dir: Directory where checkout is located.
    cur_host: Name of the current host.

  Returns:
    True if host should be converted, False otherwise.
  """
  if os.path.isdir(os.path.join(b_dir, 'build', '.svn')):
    state = 'SVN'
  elif os.path.isdir(os.path.join(b_dir, 'build', '.git')):
    state = 'GIT'
  else:
    state = 'UNKNOWN'

  try:
    url = ('https://svn-to-git-tracking.appspot.com/api/reportState?host=%s&'
           'state=%s' % (urllib2.quote(cur_host), urllib2.quote(state)))
    return json.load(urllib2.urlopen(url))
  except Exception:
    return False


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-m', '--manual', action='store_true', default=False,
                      help='Run in manual mode')
  parser.add_argument('--leak-tmp-dir', action='store_true', default=False,
                      help='Leaves temporary checkout dir on disk')
  options = parser.parse_args()

  # Find b directory.
  b_dir = None
  if is_win:
    if os.path.exists('E:\\b'):
      b_dir = 'E:\\b'
    elif os.path.exists('C:\\b'):
      b_dir = 'C:\\b'
  elif os.path.exists('/b'):
    b_dir = '/b'
  assert b_dir is not None and os.path.isdir(b_dir), 'Did not find b dir'

  # Report state before doing anything else, so we can keep track of the state
  # of this host even if something later in this script fails.
  cur_host = socket.gethostname()
  if not options.manual and not report_host_state(b_dir, cur_host):
    print 'Host %s is not pending SVN-to-Git conversion' % cur_host
    return 0

  # Set up credentials for the download_from_google_storage hook.
  env = os.environ.copy()
  boto_file = os.path.join(b_dir, 'build', 'site_config', '.boto')
  if os.path.isfile(boto_file):
    env['AWS_CREDENTIAL_FILE'] = boto_file

  # Add depot_tools to PATH, so that gclient can be found.
  env_path_sep = ';' if is_win else ':'
  env['PATH'] = '%s%s%s' % (env['PATH'], env_path_sep,
                            os.path.join(b_dir, 'depot_tools'))

  # Find old .gclient config.
  gclient_path = os.path.join(b_dir, '.gclient')
  assert os.path.isfile(gclient_path), 'Did not find old .gclient config'

  # Detect type of checkout.
  with open(gclient_path) as gclient_file:
    exec_env = {}
    exec gclient_file in exec_env
    solutions = exec_env['solutions']
  assert len(solutions) == 1, 'Number of solutions in .gclient is not 1'
  if not solutions[0]['url'].startswith('svn:'):
    print 'Non-SVN URL in .gclient: %s' % solutions[0]['url']
    return 0
  sol_name = solutions[0]['name']
  assert sol_name in GCLIENT_CONFIGS, 'Unknown type of checkout: ' % sol_name
  gclient_config = GCLIENT_CONFIGS[sol_name]

  prevent_reboot_path = os.path.join(os.path.expanduser('~'), 'no_reboot')
  tmpdir = tempfile.mkdtemp(dir=os.path.realpath(b_dir),
                            prefix='slave_svn_to_git')
  try:
    # Create new temp Git checkout.
    with open(os.path.join(tmpdir, '.gclient'), 'w') as gclient_file:
      gclient_file.write(gclient_config)

    # Sync both repos (SVN first since mirroring happens from SVN to Git).
    try:
      check_call(['gclient', 'sync'], cwd=b_dir, env=env)
    except subprocess.CalledProcessError:
      # On Windows, gclient sync occasionally reports 'checksum mismatch' error
      # for build/scripts/slave/recipes/deterministic_build.expected/
      # full_chromium_swarm_linux_deterministic.json when calling 'svn update'
      # on 'build' directory. As a workaround, we delete parent dir containing
      # invalid .svn files and try again. The missing directory should be
      # re-created with the correct checksum by repeated call to 'svn update'.
      if is_win:
        parent_dir = os.path.join(b_dir, 'build', 'scripts', 'slave', 'recipes',
                                  'deterministic_build.expected')
        check_call(['rmdir', parent_dir, '/s', '/q'], cwd=b_dir, env=env)
        check_call(['gclient', 'sync'], cwd=b_dir, env=env)
      else:
        raise

    check_call(['gclient', 'sync'], cwd=tmpdir, env=env)

    # Find repositories handled by gclient.
    revinfo = check_output(['gclient', 'revinfo'], cwd=tmpdir, env=env)
    repos = {}
    for line in revinfo.splitlines():
      relpath, repospec = line.split(':', 1)
      repos[relpath.strip()] = repospec.strip()

    # Sanity checks.
    for relpath in sorted(repos):
      # Only process directories that have .svn dir in them.
      if not os.path.isdir(os.path.join(b_dir, relpath, '.svn')):
        print '%s subdir does not have .svn directory' % relpath
        del repos[relpath]
        continue
      # Make sure Git directory exists.
      assert os.path.isdir(os.path.join(tmpdir, relpath, '.git'))

    # Prevent slave from rebooting unless no_reboot already exists.
    if not os.path.exists(prevent_reboot_path):
      with open(prevent_reboot_path, 'w') as prevent_reboot_file:
        prevent_reboot_file.write(PREVENT_REBOOT_FILE_CONTENT)

    # Move SVN .gclient away so that no one can run gclient sync while
    # conversion is in progress.
    print 'Moving .gclient to .gclient.svn in %s' % b_dir
    shutil.move(gclient_path, '%s.svn' % gclient_path)

    # Rename all .svn directories into .svn.backup.
    svn_dirs = []
    count = 0
    print 'Searching for .svn folders'
    for root, dirs, _files in os.walk(b_dir):
      count += 1
      if count % 100 == 0:
        print 'Processed %d directories' % count
      if '.svn' in dirs:
        svn_dirs.append(os.path.join(root, '.svn'))
        dirs.remove('.svn')
    for rel_svn_dir in svn_dirs:
      svn_dir = os.path.join(b_dir, rel_svn_dir)
      print 'Moving %s to %s.backup' % (svn_dir, svn_dir)
      shutil.move(svn_dir, '%s.backup' % svn_dir)

    # Move Git directories from temp dir to the checkout.
    for relpath, repospec in sorted(repos.iteritems()):
      src_git = os.path.join(tmpdir, relpath, '.git')
      dest_git = os.path.join(b_dir, relpath, '.git')
      print 'Moving %s to %s' % (src_git, dest_git)
      shutil.move(src_git, dest_git)

    # Revert any local modifications after the conversion to Git.
    home_dir = os.path.realpath(os.path.expanduser('~'))
    for relpath in sorted(repos):
      abspath = os.path.join(b_dir, relpath)
      diff = check_output(['git', 'diff'], cwd=abspath)
      if diff:
        diff_name = '%s.diff' % re.sub('[^a-zA-Z0-9]', '_', relpath)
        with open(os.path.join(home_dir, diff_name), 'w') as diff_file:
          diff_file.write(diff)
        check_call(['git', 'reset', '--hard'], cwd=abspath)

    # Update .gclient file to reference Git DEPS.
    with open(os.path.join(b_dir, '.gclient'), 'w') as gclient_file:
      gclient_file.write(gclient_config)
  finally:
    # Remove the temporary directory.
    if not options.leak_tmp_dir:
      shutil.rmtree(tmpdir)

    # Remove no_reboot file if it was created by this script.
    if os.path.isfile(prevent_reboot_path):
      with open(prevent_reboot_path, 'r') as prevent_reboot_file:
        prevent_reboot_content = prevent_reboot_file.read()
      if prevent_reboot_content == PREVENT_REBOOT_FILE_CONTENT:
        os.unlink(prevent_reboot_path)

  # Run gclient sync again.
  check_call(['gclient', 'sync'], cwd=b_dir, env=env)

  # Report state again, since we've converted to Git.
  report_host_state(b_dir, cur_host)

  return 0


if __name__ == '__main__':
  print 'Running slave_svn_to_git on %s UTC' % datetime.datetime.utcnow()
  try:
    retcode = main()
  except Exception as e:
    traceback.print_exc(e)
    retcode = 1
  print 'Return code: %d' % retcode
  sys.exit(retcode)
