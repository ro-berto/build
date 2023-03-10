#!/usr/bin/env python3
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Prints an annotation with the Clang revision used for the current build."""

import json
import optparse
import os
import subprocess
import sys

def main(argv):
  option_parser = optparse.OptionParser()
  option_parser.add_option('--output-json',
                           help='path to a json output file')
  option_parser.add_option('--src-dir', default='src',
                           help='path to the top-level sources directory')
  option_parser.add_option('--use-tot-clang', action='store_true',
                           help='tip-of-tree clang was used')
  (options, _) = option_parser.parse_args(argv)

  update_script = os.path.join(os.path.abspath(options.src_dir),
      'tools', 'clang', 'scripts', 'update.py')

  args = [sys.executable, update_script, '--print-revision']
  if options.use_tot_clang:
    args.append('--llvm-force-head-revision')

  revision = subprocess.check_output(args).rstrip().decode()
  print('Got revision: %s' % revision)

  if options.output_json:
    with open(options.output_json, 'w') as f:
      json.dump({'clang_revision': str(revision)}, f)

  return 0

if '__main__' == __name__:
  sys.exit(main(sys.argv))
