#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Prints an annotation with the Clang revision used for the current build."""

import optparse
import os
import subprocess
import sys

def main(argv):
  option_parser = optparse.OptionParser()
  option_parser.add_option('--src-dir', default='src',
                           help='path to the top-level sources directory')
  (options, _) = option_parser.parse_args(argv)

  update_script = os.path.join(os.path.abspath(options.src_dir),
      'tools', 'clang', 'scripts', 'update.py')
  revision = subprocess.check_output(
      ['python', update_script, '--print-revision'])
  print '@@@SET_BUILD_PROPERTY@got_clang_revision@"%s"@@@' % revision.rstrip()

  return 0

if '__main__' == __name__:
  sys.exit(main(sys.argv))
