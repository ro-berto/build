#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script merges code coverage profiles from multiple steps."""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import merger


def _MergeStepsArgumentParser(*args, **kwargs):
  parser = argparse.ArgumentParser(*args, **kwargs)
  parser.add_argument('--input-dir', required=True, help=argparse.SUPPRESS)
  parser.add_argument(
      '--output-file', required=True, help='where to store the merged data')
  parser.add_argument(
      '--llvm-profdata', required=True, help='path to llvm-profdata executable')
  return parser


def main():
  desc = "Merge profdata files in <--input-dir> into a single profdata."
  parser = _MergeStepsArgumentParser(description=desc)
  params = parser.parse_args()
  merger.MergeProfiles(params.input_dir, params.output_file, '.profdata',
                       params.llvm_profdata)


if __name__ == '__main__':
  sys.exit(main())
