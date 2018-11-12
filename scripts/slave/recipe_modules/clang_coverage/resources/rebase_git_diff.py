#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script maps the added lines of 'git diff' between two revisions.

For example:

File 'test.txt' in revision 1 has two lines:
line 1
line 2

A uncommitted patch changes line 2:
line 1
line 2: made some changes

So, the diff of the patch based on revision 1 is:
diff --git a/test_file.txt b/test_file.txt
index 7bba8c8e64..f5111912f3 100644
--- a/test_file.txt
+++ b/test_file.txt
@@ -1,2 +1,2 @@
 line 1
-line 2
+line 2: made some changes

Later, in revision 2, some other CL changed 'test.txt' as well:
A new line added by some other CL
line 1
line 2

After rebasing the patch to be rebased on revision 2, the diff becomes:
diff --git a/test_file.txt b/test_file.txt
index 472077838b..44a2139a41 100644
--- a/test_file.txt
+++ b/test_file.txt
@@ -1,3 +1,3 @@
 A new line added by some other CL
 line 1
-line 2
+line 2: made some changes

In revision 1, the changed line number is 2, however, in revision 2, it's 3, and
what this script does is to make a connection between them, and the main use
case is to present the code coverage data generated based on one revision to
code review tool where the diff is based on a different revision.

for more details and examples on 'git diff', please refer to:
https://git-scm.com/docs/git-diff.
"""

import argparse
from collections import defaultdict
import json
import os
import re
import sys

# Identifies the new file.
# For example: '+++ b/start_from_source_root/path/test.cc'
_NEW_FILE_PREFIX = '+++ b/'

# Identifies diff section header, which has the following format:
# @@ -{old_start_line},{old_length} +{new_start_line},{new_length} @@
# For example: '@@ -2,8 +2,8 @@'
_DIFF_RANGE_HEADER_PREFIX = '@@'
_DIFF_RANGE_HEADER_REGEX = re.compile(r'^@@ \-(\d+),?(\d+)? \+(\d+),?(\d+)? @@')

# Identifies lines added by the new files.
# For example: '+if (num >= 0) {'
_DIFF_ADDED_LINE_PREFIX = '+'


def _parse_added_lines_from_git_diff(diff):
  """Parses the 'git diff' output and returns the line number of added lines.

  Note that this method *only* cares about the added lines.

  Args:
    diff (list of str): Output produced by running 'git diff'.

  Returns:
    A dictionary whose key is a file name that is relative to the source root,
    and the corresponding value is a list of tuples of two elements, where the
    first element is the added line, and the second is the line number.
  """
  file_to_added_lines = defaultdict(list)

  current_file = None
  current_base_line_num = None
  current_offset = None

  for line in diff:
    # E.g. '+++ b/test_file.txt'
    if line.startswith(_NEW_FILE_PREFIX):
      current_file = line[len(_NEW_FILE_PREFIX):]
      current_base_line_num = None
      current_offset = None
      continue

    # E.g. '@@ -1,3 +1,3 @@''
    if line.startswith(_DIFF_RANGE_HEADER_PREFIX):
      matched = _DIFF_RANGE_HEADER_REGEX.match(line)
      if not matched:
        raise RuntimeError(
            'This script doesn\'t understand the diff section header: "%s".' %
            line)

      current_base_line_num = int(matched.group(3))
      current_offset = 0
      continue

    # E.g. ' unchanged line' and '\n'.
    is_unchanged_line = line.startswith(' ') or line == ''
    if is_unchanged_line and current_base_line_num is not None:
      current_offset += 1
      continue

    # E.g. '+made some change to this line'
    is_new_line = line.startswith(_DIFF_ADDED_LINE_PREFIX)
    if is_new_line and current_base_line_num is not None:
      line_num = current_base_line_num + current_offset
      file_to_added_lines[current_file].append((line[1:], line_num))
      current_offset += 1

  return file_to_added_lines


def generate_diff_mapping(local_diff, gerrit_diff):
  """Generates a mapping of added files between two diffs.

  Args:
    local_diff: Diff produced by running 'git diff' locally.
    gerrit_diff: Diff fetched from Gerrit.

  Returns:
    A map whose key is a file name that is relative to the source root, and the
    corresponding value is another map that maps from local diff's line number
    to Gerrit diff's line number as well as the line itself.
  """
  local_file_to_added_lines = _parse_added_lines_from_git_diff(local_diff)
  gerrit_file_to_added_lines = _parse_added_lines_from_git_diff(gerrit_diff)

  file_to_line_num_mapping = {}
  for file_name in local_file_to_added_lines:
    if file_name not in gerrit_file_to_added_lines:
      raise RuntimeError(
          'Diff mismatch. File name: "%s" is present in local diff, but not '
          'Gerrit diff.' % file_name)

    local_added_lines = local_file_to_added_lines[file_name]
    gerrit_added_lines = gerrit_file_to_added_lines[file_name]
    if len(local_added_lines) != len(gerrit_added_lines):
      raise RuntimeError(
          'Diff mismatch. Local diff has %d added lines, but Gerrit diff has '
          '%d.' % (len(local_added_lines), len(gerrit_added_lines)))

    line_num_mapping = {}
    for i in range(len(local_added_lines)):
      local_line, local_line_num = local_added_lines[i]
      gerrit_line, gerrit_line_num = gerrit_added_lines[i]
      if local_line != gerrit_line:
        raise RuntimeError(
            'Diff mistmatch. Local diff added "%s" on line %d, but Gerrit diff '
            'has "%s" on line %d.' % (local_line, local_line_num, gerrit_line,
                                      gerrit_line_num))

      # The line itself is not absoluately necessary, but is is kept for
      # debugging purpose.
      line_num_mapping[local_line_num] = (gerrit_line_num, local_line)

    file_to_line_num_mapping[file_name] = line_num_mapping

  return file_to_line_num_mapping


def _parse_args():
  arg_parser = argparse.ArgumentParser()
  arg_parser.usage = __doc__

  arg_parser.add_argument(
      '--local-diff-file',
      required=True,
      type=str,
      help='Path to a file that contains output produced by running "git diff" '
      'locally.')

  arg_parser.add_argument(
      '--gerrit-diff-file',
      required=True,
      type=str,
      help='Path to a file that contains diff of a patchset fetched from '
      'Gerrit, and the format is expected to be the same as the one produced '
      'by "git diff".')

  arg_parser.add_argument(
      '--output-file',
      required=True,
      type=str,
      help='Path to a file where the line number mapping is written to, and '
      'the format of the mapping is a map whose key is a file name that is '
      'relative to the source root, and the corresponding value is another map '
      'that maps from local diff\'s line number to Gerrit diff\'s line number '
      'as well as the line itself.')

  return arg_parser.parse_args()


def main():
  args = _parse_args()

  if not os.path.isfile(args.local_diff_file):
    raise RuntimeError(
        'Local diff file: "%s" doesn\'t exist.' % args.local_diff_file)

  if not os.path.isfile(args.gerrit_diff_file):
    raise RuntimeError(
        'Gerrit diff file "%s" doesn\'t exist.' % args.gerrit_diff_file)

  with open(args.local_diff_file) as f:
    local_diff = [line.rstrip() for line in f]

  with open(args.gerrit_diff_file) as f:
    gerrit_diff = [line.rstrip() for line in f]

  file_to_line_num_mapping = generate_diff_mapping(local_diff, gerrit_diff)
  json_mapping = json.dumps(file_to_line_num_mapping)
  with open(args.output_file, 'w') as f:
    f.write(json_mapping)

  sys.stdout.write(json_mapping)


if __name__ == '__main__':
  sys.exit(main())
