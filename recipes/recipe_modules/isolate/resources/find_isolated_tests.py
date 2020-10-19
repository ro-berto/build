#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Scans build output directory for .isolated files, calculates their SHA1
hashes and stores final list in JSON document.

Used to figure out what tests were build in isolated mode to trigger these
tests to run on swarming.

For more info see:
https://sites.google.com/a/chromium.org/dev/developers/testing/isolated-testing
"""

import glob
import optparse
import os
import re
import sys


def main():
  parser = optparse.OptionParser(
      usage='%prog --build-dir <path>',
      description=sys.modules[__name__].__doc__)
  parser.add_option(
      '--build-dir',
      help='Path to a directory to search for *.isolated files.')

  options, _ = parser.parse_args()
  if not options.build_dir:
    parser.error('--build-dir option is required')

  result = {}

  # Clean up generated *.isolated.gen.json files produced by mb.
  pattern = os.path.join(options.build_dir, '*.isolated.gen.json')
  for filepath in sorted(glob.glob(pattern)):
    os.remove(filepath)

  # Clean up enerated *.isolated files produced by mb.
  pattern = os.path.join(options.build_dir, '*.isolated')
  for filepath in sorted(glob.glob(pattern)):
    test_name = os.path.splitext(os.path.basename(filepath))[0]
    if re.match(r'^.+?\.\d$', test_name):
      # It's a split .isolated file, e.g. foo.0.isolated. Ignore these.
      continue

    # TODO(csharp): Remove deletion entirely once the isolate
    # tracked dependencies are inputs for the isolated files.
    # http://crbug.com/419031
    os.remove(filepath)

  return 0


if __name__ == '__main__':
  sys.exit(main())
