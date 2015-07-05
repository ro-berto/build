#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback


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


def main():
  # Find b directory.
  b_dir = None
  if is_win:
    if os.path.exists('E:\\b'):
      b_dir = 'E:\\b'
    elif os.path.exists('C:\\b'):
      b_dir = 'C:\\b'
  elif os.path.exists('/b'):
    b_dir = '/b'
  assert os.path.isdir(b_dir), 'Did not find b dir'

  # Set up credentials for the download_from_google_storage hook.
  env = os.environ.copy()
  boto_file = os.path.join(b_dir, 'build', 'site_config', '.boto')
  if os.path.isfile(boto_file):
    env['AWS_CREDENTIAL_FILE'] = boto_file

  # Find old .gclient config.
  gclient_path = os.path.join(b_dir, '.gclient')
  assert os.path.isfile(gclient_path), 'Did not find old .gclient config'

  # Detect type of checkout.
  solutions = []
  with open(gclient_path) as gclient_file:
    exec gclient_file
  assert len(solutions) == 1, 'More than one solution in .gclient'
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
    revinfo = check_output(['gclient', 'revinfo'], cwd=tmpdir)
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
  print 'Running slave_svn_to_git on %s UTC' % datetime.datetime.now()
  try:
    retcode = main()
  except Exception as e:
    traceback.print_exc(e)
    retcode = 1
  print 'Return code: %d' % retcode
  sys.exit(retcode)
