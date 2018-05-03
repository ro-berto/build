#!/usr/bin/env python
# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to extract size information from a build.
"""

import argparse
import os
import sys
import json


def get_size(path):
  if os.path.isdir(path):
    total = 0
    for root, _, files in os.walk(path):
      for f in files:
        total += os.path.getsize(os.path.join(root, f))
    return total
  else:
    return os.path.getsize(path)


def main(argv):
  """Print the size of files specified to it as loose args."""

  parser = argparse.ArgumentParser()
  parser.add_argument('--output', type=argparse.FileType('w'),
                      default=sys.stdout, help='path to the JSON output file')
  parser.add_argument('files', nargs='+')
  parser.add_argument('--base-dir', default='.')

  options = parser.parse_args(argv)

  sizes = {}
  for filename in options.files:
    sizes[filename] = get_size(os.path.join(options.base_dir, filename))

  json.dump(sizes, options.output)

  return 0

if '__main__' == __name__:
  sys.exit(main(sys.argv[1:]))
