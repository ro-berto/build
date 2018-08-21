#!/usr/bin/env python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import time

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--swarming-server', required=True)
  parser.add_argument('--swarming-py-path', required=True)
  parser.add_argument('--json', required=True)
  parser.add_argument('task_id', nargs='+')

  args = parser.parse_args()

  url = 'tasks/get_states?'
  for task in args.task_id:
    url += 'task_id=%s' % task

  cmd = [
      args.swarming_py_path,
      'query',
      '-S', args.swarming_server,
      '--json=%s' % args.json,
      url,
  ]

  logging.info('get_states cmd: %s', ' '.join(cmd))
  get_states_result = subprocess.call(cmd)
  if collect_result != 0:
    logging.warn(
        'get_states cmd had non-zero return code: %s', get_states_result)

  return 0

if __name__ == '__main__':
  sys.exit(main())
