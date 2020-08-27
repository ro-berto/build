#!/usr/bin/env vpython
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test runner wrapper for tricium_clang_tidy.py

We want a cheap way of catching any obvious py3 incompatibilities. This runs
all tests under py2 and, if the necessary bits just-so-happen to be available,
py3.

The only necessary bit on top of py3 is a `yaml` library, which comes
preinstalled on some distros. Unfortunately, we don't have a py3 pyyaml wheel
in cipd at the time of writing.
"""

from __future__ import print_function

import argparse
import errno
import multiprocessing
import multiprocessing.pool
import os
import os.path
import subprocess
import sys


class _MissingDependencyError(Exception):

  def __init__(self, *args, **kwargs):
    super(_MissingDependencyError, self).__init__(*args, **kwargs)


def _run_under_py3(test_file, test_args):
  try:
    subprocess.check_output(['python3', '-c', 'import yaml'],
                            stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError:
    raise _MissingDependencyError('yaml')
  except OSError as e:
    if e.errno != errno.ENOENT:
      raise
    raise _MissingDependencyError('python3')

  return subprocess.check_output(
      ['python3', test_file] + test_args,
      stderr=subprocess.STDOUT).decode('utf-8', 'ignore')


def main():
  # Only so we DTRT for --help.
  _, test_args = argparse.ArgumentParser(
      description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter).parse_known_args()

  my_dir = os.path.dirname(os.path.realpath(__file__))
  test_file = os.path.join(my_dir, 'tricium_clang_tidy_test_impl.py')

  smol_pool = multiprocessing.pool.ThreadPool(processes=1)
  py3_result = smol_pool.apply_async(_run_under_py3, (test_file, test_args))
  smol_pool.close()

  test_args.insert(0, '--using_hacky_test_runner')
  try:
    print('Testing under py2...')
    if subprocess.call(['vpython', test_file] + test_args):
      sys.exit(1)

    print('\nTesting under py3...')
    try:
      output = py3_result.get()
      print(output)
    except _MissingDependencyError as e:
      print('** Skipped; looks like we lack %s' % e.args[0])
    except subprocess.CalledProcessError as e:
      print(e.output)
      sys.exit(1)
  finally:
    smol_pool.join()


if __name__ == '__main__':
  main()
