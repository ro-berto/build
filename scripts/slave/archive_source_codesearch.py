#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to create tarball from chromium source code

This script is created instead of just running commands from recipe because
recipe does not support pipe."""


import argparse
import os
import subprocess
import sys
import time


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-f', '--file', dest='filename',
                      help='archive file name', metavar='FILE')
  parser.add_argument('-g', '--generated_file', dest='generated_filename',
                      help='archive file name for just generated files',
                      metavar='FILE')
  parser.add_argument('directories', nargs='+',
                      help='directories to be included in the archive')
  options = parser.parse_args()
  filename = options.filename or 'chromium.tar.bz2'

  for d in options.directories:
    if not os.path.exists(d):
      raise Exception('ERROR: no %s directory to package, exiting' % d)

  if not create_archive(options.directories, filename):
    return 1

  if options.generated_filename:
    if not create_generated_code_archive('src/out', options.generated_filename):
      return 1

  return 0


def create_archive(directories, output_filename):
  """Archives everything - both source and generated files."""

  print '%s: Creating tar file %s...' % (time.strftime('%X'), output_filename)
  find_command = ['find'] + directories + [
      '-type', 'f', '-size', '-10M',
      # The only files under src/out we want to package up are generated
      # sources.
      '(', '-regex', '^src/out/[^/]*/gen/.*', '-o',
      '!', '-regex', '^src/out/.*', ')',
      # Exclude all .svn and .git directories, the native client toolchain and
      # the llvm build directory, and perf/data files.
      '-a', '!', '-regex', r'.*\.svn.*',
      '-a', '!', '-regex', r'.*\.git.*',
      '-a', '!', '-regex', '^src/data/.*',
      '-a', '!', '-regex', '^src/native_client/toolchain/.*',
      '-a', '!', '-regex', '^src/third_party/llvm-build/.*',
      '-a', '!', '-regex', '^tools/perf/data/.*',
  ]

  return find_and_tar(find_command, output_filename)


def create_generated_code_archive(directory, output_filename):
  """Archives just the generated files."""

  print '%s: Creating tar file of just generated code %s...' % (
      time.strftime('%X'), output_filename)
  find_command = ['find', '.'] + [
      '-type', 'f', '-size', '-10M',
      # The only files under src/out we want to package up are generated
      # sources.
      '(', '-regex', '^\./[^/]*/gen/.*', '-o',
      '!', '-regex', '^\./.*', ')',
      # Exclude all .svn and .git directories.
      '-a', '!', '-regex', r'.*\.svn.*',
      '-a', '!', '-regex', r'.*\.git.*',
  ]

  return find_and_tar(find_command, output_filename, cwd=directory)


def find_and_tar(find_command, output_filename, cwd=None):
  find_proc = subprocess.Popen(find_command, stdout=subprocess.PIPE, cwd=cwd)
  tar_proc = subprocess.Popen(['tar', '-T-', '-cjvf',
                               os.path.abspath(output_filename)],
                              stdin=find_proc.stdout, cwd=cwd)
  find_proc.stdout.close()
  find_proc.wait()
  tar_proc.communicate()
  return (tar_proc.returncode == 0 and find_proc.returncode == 0)



if '__main__' == __name__:
  sys.exit(main())
