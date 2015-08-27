#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import datetime
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

WHITELISTED_HOSTS = [
  # Initial slaves to test script on.
  'slave101-c4', 'slave102-c4', 'slave103-c4', 'slave104-c4', 'slave105-c4',
  'slave106-c4', 'slave107-c4', 'slave108-c4', 'slave109-c4', 'slave110-c4',

  # All slaves on chromium.fyi.
  'build1-m1', 'build4-m1', 'build5-a1', 'build27-m1', 'build28-m1',
  'build29-m1', 'build38-a1', 'build58-m1', 'build60-m1', 'build61-m1',
  'build63-a1', 'build70-m1', 'build84-a1', 'build85-a1', 'build85-m1',
  'build87-a95', 'build97-m1', 'build98-m1', 'build99-m1', 'build127-m1',
  'build128-m1', 'build129-m1', 'build130-m1', 'build154-m1', 'chromeperf80',
  'chromeperf87', 'panda8', 'slave3-c1', 'slave4-c1', 'slave5-c1', 'slave20-c1',
  'vm9-m1', 'vm12-m1', 'vm17-m1', 'vm49-m1', 'vm52-m1', 'vm190-m1', 'vm191-m1',
  'vm310-m1', 'vm311-m1', 'vm312-m1', 'vm313-m1', 'vm448-m1', 'vm452-m1',
  'vm455-m1', 'vm471-m1', 'vm480-m1', 'vm481-m1', 'vm482-m1', 'vm498-m1',
  'vm634-m1', 'vm641-m1', 'vm646-m1', 'vm649-m1', 'vm650-m1', 'vm657-m1',
  'vm658-m1', 'vm678-m1', 'vm683-m1', 'vm687-m1', 'vm693-m1', 'vm800-m1',
  'vm803-m1', 'vm820-m1', 'vm821-m1', 'vm823-m1', 'vm832-m1', 'vm835-m1',
  'vm845-m1', 'vm847-m1', 'vm848-m1', 'vm859-m1', 'vm866-m1', 'vm877-m1',
  'vm879-m1', 'vm889-m1', 'vm899-m1', 'vm909-m1', 'vm912-m1', 'vm928-m1',
  'vm929-m1', 'vm933-m1', 'vm939-m1', 'vm943-m1', 'vm950-m1', 'vm951-m1',
  'vm954-m1', 'vm961-m1', 'vm962-m1', 'vm970-m1', 'vm973-m1', 'vm974-m1',
  'vm976-m1', 'vm977-m1', 'vm978-m1', 'vm992-m1', 'vm993-m1', 'vm994-m1',
  'vm999-m1',
]

is_win = sys.platform.startswith('win')


def check_call(cmd, cwd=None, env=None):
  print 'Running %s%s' % (cmd, ' in %s' % cwd if cwd else '')
  subprocess.check_call(cmd, cwd=cwd, shell=is_win, env=env)


def check_output(cmd, cwd=None, env=None):
  print 'Running %s%s' % (cmd, ' in %s' % cwd if cwd else '')
  return subprocess.check_output(cmd, cwd=cwd, shell=is_win, env=env)


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

  # Report host state to the tracking app.
  cur_host = socket.gethostname()
  if os.path.isdir(os.path.join(b_dir, 'build', '.svn')):
    state = 'SVN'
  elif os.path.isdir(os.path.join(b_dir, 'build', '.git')):
    state = 'GIT'
  else:
    state = 'UNKNOWN'

  try:
    url = ('https://svn-to-git-tracking.appspot.com/api/reportState?host=%s&'
           'state=%s' % (urllib2.quote(cur_host), urllib2.quote(state)))
    urllib2.urlopen(url)
  except Exception:
    pass

  # Check if host is whitelisted.
  if not options.manual:
    if not any(host.lower() in cur_host.lower() for host in WHITELISTED_HOSTS):
      print 'Host %s is not whitelisted for SVN-to-Git conversion' % cur_host
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
    check_call(['gclient', 'sync'], cwd=b_dir, env=env)
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
