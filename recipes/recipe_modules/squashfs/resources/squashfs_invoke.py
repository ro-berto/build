# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import subprocess
import sys


def ProcessOptions():
  """Process options from command line."""
  argparser = argparse.ArgumentParser(add_help=False)
  argparser.add_argument(
      '--binary-path', help='Absolute binary path to execute.')
  argparser.add_argument('--folder', help='Folder to compress')
  argparser.add_argument('--output-file', help='Output file')
  args = argparser.parse_args()
  return args


def Mksquashfs(binary_path, folder_to_compress, output_file_path):
  subprocess.check_call([binary_path, folder_to_compress, output_file_path])


def main():
  args = ProcessOptions()
  Mksquashfs(args.binary_path, args.folder, args.output_file)


if '__main__' == __name__:
  sys.exit(main())
