# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys
import os
import subprocess

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BUILD = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

def main(argv):
  path = os.environ.get('PYTHONPATH', '')
  path = path.split(':')
  def add(new_path):
    if new_path not in path:
      path.append(new_path)

  third_party = os.path.join(BUILD, 'third_party')
  for d in os.listdir(third_party):
    full = os.path.join(third_party, d)
    if os.path.isdir(full):
      add(full)
  add(os.path.join(BUILD, 'scripts'))
  add(third_party)
  add(os.path.join(BUILD, 'site_config'))
  add(os.path.join(BUILD, '..', 'build_internal', 'site_config'))
  add('.')
  os.environ['PYTHONPATH'] = os.pathsep.join(path)
  print 'Set PYTHONPATH: %s' % os.environ['PYTHONPATH']

  # Use subprocess instead of execv because otherwise windows destroys quoting.
  p = subprocess.Popen(argv[1:])
  p.wait()
  return p.returncode


if __name__ == '__main__':
  sys.exit(main(sys.argv))
