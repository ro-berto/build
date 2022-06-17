#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script generates the line number mapping from bot to Gerrit.

For example:

On Gerrit, 'test.txt' is generated by applying my change to base revision 10:
#1: line 1
#2: line 2, changed by me
#3: line 3

On the bot, 'test.txt' is generated by applying my change to base revision 12:
#1: line 0, added by someone else
#2: line 1, changed by someone else
#3: line 2, changed by me

After rebasing the line numbers, we'd like understand that
'line 2, changed by me' exists in both files (it should, because both two files
contain my change), and their line number mapping is 2 -> 3.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile

import diff_util
import gerrit_util


def rebase_line_number(host, project, change, patchset, src_path, sources):
  """Rebases line number for a list of files from bot to gerrit.

  Args:
    host (str): The url of the Gerrit host.
    project (str): The Gerrit project name.
    change (int): The Gerrit change number.
    patchset (int): The Gerrit patchset number.
    src_path (str): Absoluate path to the root of the checkout.
    sources (list): A list of relative path to the source files that were added
      or modified by the patchset. Deleted files should not be included in this
      list or else requests to Gerrit to fetch file content will error.

  Returns:
    A map whose key is a file name that is relative to the root of the checkout,
    and the corresponding value is another map that maps from local file's line
    number to Gerrit file's line number as well as the line itself.
  """
  gerrit_files_content = gerrit_util.fetch_files_content(
      host, project, change, patchset, sources)
  assert len(sources) == len(gerrit_files_content), (
      'Number of files to rebase is expected to be the same as number of files '
      'have file content fetched from Gerrit')

  file_to_line_num_mapping = {}
  for filename, content in zip(sources, gerrit_files_content):
    local_file_path = os.path.join(src_path, filename)
    gerrit_file_path = None
    # On Windows, the file returned by NamedTemporaryFile cannot be opened a
    # second time by its name until it has been closed. Therefore we must ensure
    # it is closed before passing its name to the subprocess.
    with tempfile.NamedTemporaryFile(delete=False) as gerrit_file:
      gerrit_file.write(content)
      gerrit_file_path = gerrit_file.name
    try:
      diff_cmd = [
          'git', 'diff', '--no-index', local_file_path, gerrit_file_path
      ]
      diff_output = None
      logging.info('Calculating diff b/w bot file %s and gerrit file %s',
                   local_file_path, gerrit_file_path)
      # 'diff' command returns 0 if two files are the same, 1 if differences are
      # found, >1 if an error occurred.
      diff_output = subprocess.check_output(diff_cmd)
    except subprocess.CalledProcessError as e:
      if e.returncode != 1:
        raise
      diff_output = e.output
    finally:
      os.remove(gerrit_file_path)

    diff_lines = diff_output.splitlines()
    with open(local_file_path) as f:
      local_lines = f.read().splitlines()
    gerrit_lines = content.splitlines()
    file_to_line_num_mapping[filename] = (
        diff_util.generate_line_number_mapping(diff_lines, local_lines,
                                               gerrit_lines))

  return file_to_line_num_mapping


def _parse_args():
  arg_parser = argparse.ArgumentParser()
  arg_parser.usage = __doc__

  arg_parser.add_argument(
      '--host', required=True, type=str, help='The url of the Gerrit host.')

  arg_parser.add_argument(
      '--project', required=True, type=str, help='The Gerrit project name')

  arg_parser.add_argument(
      '--change', required=True, type=int, help='The Gerrit change number.')

  arg_parser.add_argument(
      '--patchset', required=True, type=int, help='The Gerrit patchset number.')

  arg_parser.add_argument(
      '--src-path',
      required=True,
      type=str,
      help='absolute path to the root of the checkout')

  arg_parser.add_argument(
      '--output-file',
      required=True,
      type=str,
      help='Path to a file where the line number mapping is written to, and '
      'the format of the mapping is a map whose key is a file name that is '
      'relative to the root of the checkout, and the corresponding value is '
      'another map that maps from local file\'s line number to Gerrit file\'s '
      'line number as well as the line itself.')

  arg_parser.add_argument(
      'sources',
      nargs='+',
      help='Paths of source files to line number mapping for, the paths are '
      'relative to the root of the checkout, with platform-specific path '
      'separator.')

  return arg_parser.parse_args()


def main():
  args = _parse_args()

  logging.basicConfig(
      level=logging.INFO, format='[%(asctime)s %(levelname)s] %(message)s')
  if not os.path.isdir(args.src_path):
    raise RuntimeError('Checkout: "%s" doesn\'t exist.' % args.src_path)

  file_to_line_num_mapping = rebase_line_number(args.host, args.project,
                                                args.change, args.patchset,
                                                args.src_path, args.sources)
  json_mapping = json.dumps(file_to_line_num_mapping)
  with open(args.output_file, 'w') as f:
    f.write(json_mapping)

  sys.stdout.write(json_mapping)


if __name__ == '__main__':
  sys.exit(main())
