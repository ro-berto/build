# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import os
import re
import subprocess
import sys


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--image', required=True,
      help='Image in which command will be executed.')
  parser.add_argument(
      '--config-file', required=True,
      help='Location of the Docker config file.')
  parser.add_argument(
      '--dir-map', metavar=('HOST_DIR', 'DOCKER_PATH'), nargs=2,
      action='append', default=[],
      help='Directories to be mapped in host_path:docker_path. Host paths '
           'that do not exist will be created before running docker to make '
           'sure that they are owned by current user.')

  # Extract command specified after -- before parsing script args.
  script_args = sys.argv[1:sys.argv.index('--')]
  command = sys.argv[sys.argv.index('--') + 1:]
  args = parser.parse_args(script_args)

  cmd = [
    'docker',
    '--config', args.config_file,
    'run',
    '--user', '%s:%s' % (os.getuid(), os.getgid())
  ]

  for host_path, docker_path in args.dir_map:
    # Ensure that host paths exist, otherwise they will be created by the docker
    # command, which makes them owned by root and thus hard to remove/modify.
    if not os.path.exists(host_path):
      os.makedirs(host_path)
    elif not os.path.isdir(host_path):
      parser.error('Cannot map non-directory host path: %s' % host_path)
    cmd.extend(['--volume', '%s:%s' % (host_path, docker_path)])

  cmd.append(args.image)
  cmd.extend(command)
  try:
    subprocess.check_call(cmd)
  except subprocess.CalledProcessError as e:
    return e.returncode


if __name__ == '__main__':
  sys.exit(main())
