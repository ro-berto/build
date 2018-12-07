#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Traverses the output dir and aggregates 'invalid_profiles.json' instances."""

import argparse
import json
import os
import sys


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--root-dir', required=True, help='directory to traverse')
  params = parser.parse_args()
  # Record the names of the steps for which we had to exclude some profiles from
  # the merge due to corruption or malformedness.
  steps_with_merge_errors = []
  for path, _dirs, files in os.walk(params.root_dir):
    if 'invalid_profiles.json' in files:
      try:
        with open(os.path.join(path, 'invalid_profiles.json')) as f:
          invalid_profiles = json.load(f)
          if invalid_profiles:
            # Note that the directory name is a modified version of the step
            # name.
            # We could pass the step name to the merge script, but seems this
            # should be enough for manual debugging.
            steps_with_merge_errors.append(os.path.basename(path))
      except ValueError:
        steps_with_merge_errors.append(
            os.path.basename(path) + '- BAD JSON FORMAT')
  json.dump(steps_with_merge_errors, sys.stdout)


if __name__ == '__main__':
  main()
