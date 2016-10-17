#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Update windows env by rewriting environment.{x86,x64}

"""

import argparse
import os
import re
import sys


def NeedEnvFileUpdateOnWin(changed_keys):
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
  for key in changed_keys:
    if key not in ignore_envs:
      return True
  return False


def UpdateWindowsEnvironment(envfile_dir, env, update_keys):
  """Update windows environment in environment.{x86,x64}.

  Args:
    envfile_dir: a directory name environment.{x86,x64} are stored.
    env: an instance of dict that represents environment.
    update_keys: list or set of keys to be updated.
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
    for key in update_keys:
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


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description='UpdateWindowsEnvironment runner')
  parser.add_argument('--envfile-dir', required=True,
                      help='envfile to be updated')

  args = parser.parse_args()

  environ = os.environ
  UpdateWindowsEnvironment(args.envfile_dir, environ, environ.keys())
