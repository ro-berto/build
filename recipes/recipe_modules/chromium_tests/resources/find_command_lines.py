#!/usr/bin/env python
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Scans build output directory for .isolate files, extracts the
command lines, and returns the map of target_name -> command line.

Used to figure out what command lines to pass to swarming tasks.
"""

import argparse
import ast
import glob
import json
import os

parser = argparse.ArgumentParser()
parser.add_argument(
    '--build-dir',
    required=True,
    help='Path to a directory to search for *.isolate files')
parser.add_argument(
    '--output-json', required=True, help='File to dump JSON results into.')
parser.add_argument(
    '--inverted',
    action='store_true',
    default=False,
    required=False,
    help='Find any inverted command lines instead.')
args = parser.parse_args()

command_line_map = {}

for path in glob.glob(os.path.join(args.build_dir, '*.isolate')):
  target_name = os.path.splitext(os.path.basename(path))[0]
  with open(path) as fp:
    isolate = ast.literal_eval(fp.read())
    if not args.inverted:
      if 'command' in isolate.get('variables', {}):
        command_line_map[target_name] = isolate['variables']['command']
    else:
      if 'inverted_command' in isolate.get('variables', {}):
        command_line_map['{}'.format(
            target_name)] = isolate['variables']['inverted_command']

with open(args.output_json, 'w') as fp:
  json.dump(command_line_map, fp)
