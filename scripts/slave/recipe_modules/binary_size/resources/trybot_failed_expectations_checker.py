#!/usr/bin/env python
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Checks for expectation failures stamp files created by enabling the gn arg
check_android_configuration. This is used by the size trybot to monitor
expectation file regressions."""

import argparse
import json
import os
import shutil


def _ClearExpectationsDir(dir_path):
  shutil.rmtree(dir_path, ignore_errors=True)


def _CheckExpectationsDir(dir_path):
  failed_expectations = []
  try:
    for failed_expectation_file in os.listdir(dir_path):
      with open(os.path.join(dir_path, failed_expectation_file)) as f:
        failed_expectations.append(f.read())
  except OSError:
    # if there is no failure directory created, then everything passed.
    pass
  return {
      'success': len(failed_expectations) == 0,
      'failed_messages': failed_expectations,
  }


def _GetExpectationsDir(build_vars_path):
  with open(build_vars_path) as f:
    build_vars = dict(l.rstrip().split('=', 1) for l in f)
    return build_vars['android_configuration_failure_dir']


def _RebasePath(path, new_cwd, old_cwd):
  """Makes the given path(s) relative to new_cwd, or absolute if not specified.

  If new_cwd is not specified, absolute paths are returned.
  """
  old_cwd = os.path.abspath(old_cwd)
  if new_cwd:
    new_cwd = os.path.abspath(new_cwd)
    return os.path.relpath(os.path.join(old_cwd, path), new_cwd)
  return os.path.abspath(os.path.join(old_cwd, path))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--clear-expectations',
      action='store_true',
      help='Delete expectations files so they dont clober a new build.')
  parser.add_argument(
      '--check-expectations',
      action='store_true',
      help='Check for the existance of failed expecation files after a build.')
  parser.add_argument(
      '--build-vars-path', required=True, help='Path to build_vars.txt.')
  parser.add_argument(
      '--results-path', help='Output path for the trybot result .json file.')
  args = parser.parse_args()

  expectations_dir = _GetExpectationsDir(args.build_vars_path)
  expectations_dir = _RebasePath(expectations_dir, os.getcwd(),
                                 os.path.dirname(args.build_vars_path))

  if args.check_expectations:
    if not args.results_path:
      parser.error('--results-path is required when passing '
                   '--check-expectations')
    result = _CheckExpectationsDir(expectations_dir)
    with open(args.results_path, 'w') as f:
      json.dump(result, f)

  if args.clear_expectations:
    _ClearExpectationsDir(expectations_dir)


if __name__ == '__main__':
  main()
