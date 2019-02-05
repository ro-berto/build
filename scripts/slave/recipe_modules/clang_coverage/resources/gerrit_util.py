#!/usr/bin/python
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script provides utility functions related to Gerrit.

One of the main functionalities is to interact with Gerrit REST APIs, and for
more details on the REST APIs of Gerrit, please refer to:
https://gerrit-review.googlesource.com/Documentation/rest-api.html.
"""

import base64
from collections import defaultdict
import json
import logging
import re
import subprocess
import time
import urllib2

# A fixed prefix in the http response.
_RESPONSE_PREFIX = ')]}\n'

# Number of times to retry a http request.
_HTTP_NUM_RETRY = 3

# Identifies diff section header, which has the following format:
# @@ -{old_start_line},{old_length} +{new_start_line},{new_length} @@
# For example: '@@ -2,8 +2,8 @@'
_DIFF_RANGE_HEADER_PREFIX = '@@'
_DIFF_RANGE_HEADER_REGEX = re.compile(r'^@@ \-(\d+),?(\d+)? \+(\d+),?(\d+)? @@')

# Identifies the line representing the info of the from file.
# For example: '--- file1.txt 2019-02-02 17:51:49.000000000 -0800'
_DIFF_FROM_FILE_PREFIX = '---'

# Identifies the line representing the info of the to file.
# For example: '+++ file.txt 2019-02-02 17:51:49.000000000 -0800'
_DIFF_TO_FILE_PREFIX = '+++'

# Identifies different lines deleted from the first file.
# For example: '-if (num >= 0) {'
_DIFF_MINUS_LINE_PREFIX = '-'

# Identifies different lines added to the the second file.
# For example: '+if (num >= 0) {'
_DIFF_PLUS_LINE_PREFIX = '+'

# Identifies unchanged line between the two files.
# For example: ' int num = 1;'
_DIFF_WHITESPACE_LINE_PREFIX = ' '


# TODO(crbug.com/927941): Remove once the Gerrit side fix is live in prod.
def fetch_diff(host, project, change, patchset):
  """Fetches diff of the patch from Gerrit.

  Args:
    host (str): The url of the host.
    project (str): The project name.
    change (int): The change number.
    patchset (int): The patchset number.

  Returns:
    A string of the fetched diff.
  """
  project_quoted = urllib2.quote(project, safe='')

  # Uses the Get Change API to get and parse the revision of the patchset.
  # https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#get-change.
  template_to_get_revisions = 'https://%s/changes/%s~%d?o=ALL_REVISIONS&o=SKIP_MERGEABLE'
  url_to_get_reivisions = template_to_get_revisions % (host, project_quoted,
                                                       change)
  response = _retry_urlopen(url_to_get_reivisions)
  change_details = json.loads(response.read()[len(_RESPONSE_PREFIX):])
  patchset_revision = None

  for revision, value in change_details['revisions'].iteritems():
    if patchset == value['_number']:
      patchset_revision = revision
      break

  if not patchset_revision:
    raise RuntimeError(
        'Patchset %d is not found in the change descriptions returned by '
        'requesting %s.' % (patchset, url_to_get_reivisions))

  # In order to get the diff, the most straightforward solution is to use the
  # Get Patch REST API:
  # https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#get-patch.
  # However, one issue with this API is that it always fails to capture the diff
  # of file renaming, and the returned diff "incorrectly" contains two sections,
  # where the first section deletes all lines of the original file, and another
  # section adds all lines of the renamed file.
  #
  # To work the above mentioned issue around, this method fetches diff from
  # gitile, for example:
  # https://chromium.googlesource.com/chromium/src/+/aa006552353f43fbec1ef328269196cbf067c66f
  template_to_get_diff = 'https://%s/%s/+/%s%%5E%%21?format=text'
  gitile_host = host.replace('-review', '')
  url_to_get_diff = template_to_get_diff % (gitile_host, project_quoted,
                                            patchset_revision)
  response = _retry_urlopen(url_to_get_diff)
  diff = base64.b64decode(response.read())
  return diff


# TODO(crbug.com/927941): Remove once the Gerrit side fix is live in prod.
def parse_added_line_num_from_git_diff(diff):
  """Parses the 'git diff' output and returns the line number of added lines.

  Note that this method *only* cares about the added lines.

  Args:
    diff (list of str): Output produced by running 'git diff'.

  Returns:
    A dictionary whose key is a file name that is relative to the source root,
    and the corresponding value a set of line numbers.
  """
  file_to_added_lines = defaultdict(set)

  current_file = None
  current_base_line_num = None
  current_offset = None

  for line in diff:
    # E.g. '+++ dev/null'
    if line.startswith('+++ /dev/null'):
      current_file = None
      current_base_line_num = None
      current_offset = None
      continue

    # E.g. '+++ b/test_file.txt'
    if line.startswith('+++ b/'):
      current_file = line[len('+++ b/'):]
      current_base_line_num = None
      current_offset = None
      continue

    if current_file is None:
      # If a file is deleted, there should be no added lines in the diff ranges.
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
    is_new_line = line.startswith('+')
    if is_new_line and current_base_line_num is not None:
      line_num = current_base_line_num + current_offset
      file_to_added_lines[current_file].add(line_num)
      current_offset += 1

  return file_to_added_lines


def fetch_files_content(host, project, change, patchset, file_paths):
  """Fetches file content for a list of files from Gerrit.

  Args:
    host (str): The url of the host.
    project (str): The project name.
    change (int): The change number.
    patchset (int): The patchset number.
    file_paths (list): A list of file paths that are relative to the checkout.

  Returns:
    A list of String where each one corresponds to the content of each file.
  """
  project_quoted = urllib2.quote(project, safe='')
  change_id = '%s~%d' % (project_quoted, change)

  # Uses the Get Change API to get and parse the revision of the patchset.
  # https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#get-change.
  url_to_get_reivisions = (
      'https://%s/changes/%s?o=ALL_REVISIONS&o=SKIP_MERGEABLE') % (host,
                                                                   change_id)
  response = _retry_urlopen(url_to_get_reivisions)
  change_details = json.loads(response.read()[len(_RESPONSE_PREFIX):])
  patchset_revision = None

  for revision, value in change_details['revisions'].iteritems():
    if patchset == value['_number']:
      patchset_revision = revision
      break

  if not patchset_revision:
    raise RuntimeError(
        'Patchset %d is not found in the change descriptions returned by '
        'requesting %s.' % (patchset, url_to_get_reivisions))

  result = []
  for file_path in file_paths:
    result.append(
        _fetch_file_content(host, change_id, patchset_revision, file_path))

  return result


def _retry_urlopen(url):
  """Retry version of urllib2.urlopen.

  Args:
    url (str): The URL.

  Returns:
    The response if status code is 200, otherwise, exception is raised.
  """
  tries = _HTTP_NUM_RETRY
  delay_seconds = 1
  while tries >= 0:
    try:
      return urllib2.urlopen(url)
    except urllib2.URLError:
      time.sleep(delay_seconds)
      tries -= 1
      delay_seconds *= 2

  raise RuntimeError('Failed to open URL: "%s".' % url)


def _fetch_file_content(host, change_id, revision, file_path):
  """Fetches file content for a single file from Gerrit.

  Args:
    host (str): The url of the host.
    change_id (str): '<project>~<numericId>'.
    revision (str): Identifier that uniquely identifies a revision of a change.
    file_path (str): File path that is relative to the checkout.

  Returns:
    A string representing the file content.
  """
  # Uses the Get Content API to get the file content from Gerrit.
  # https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#get-content
  quoted_file_path = urllib2.quote(file_path, safe='')
  url_to_get_content = ('https://%s/changes/%s/revisions/%s/files/%s/content'
                       ) % (host, change_id, revision, quoted_file_path)
  response = _retry_urlopen(url_to_get_content)
  content = base64.b64decode(response.read())
  return content


def generate_line_number_mapping(from_file_path, to_file_path):
  """Generates a mapping of unchanged between two files on the file system.

  Args:
    from_file_path (str): Absolute file path to one file.
    to_file_path (str): Absolute file path to the other file.

  Returns:
    A map that maps the line number of unchanged lines from |from_file_path| to
    |to_file_path|.
  """
  diff_cmd = ['git', 'diff', '--no-index', from_file_path, to_file_path]
  diff_output = None
  try:
    # 'diff' command returns 0 if two files are the same, 1 if differences are
    # found, >1 if an error occurred.
    diff_output = subprocess.check_output(diff_cmd)
  except subprocess.CalledProcessError as e:
    if e.returncode == 1:
      diff_output = e.output
    else:
      raise

  logging.info('The diff output between %s and %s is generated as:\n%s',
               from_file_path, to_file_path, diff_output)
  logging.info('-' * 80)
  diff_lines = diff_output.splitlines()

  with open(from_file_path, 'r') as f:
    from_file_lines = f.read().splitlines()

    # In the diff output, line number starts from 1, so manually inserts a line
    # to the beginging to simply later index related computations.
    from_file_lines.insert(0, 'Manually padded line')

  with open(to_file_path, 'r') as f:
    to_file_lines = f.read().splitlines()

    # In the diff output, line number starts from 1, so manually inserts a line
    # to the beginging to simply later index related computations.
    to_file_lines.insert(0, 'Manually padded line')

  def _verify_and_add_unchanged_line(from_file_line_num, from_file_lines,
                                     to_file_line_num, to_file_lines,
                                     line_num_mapping):
    from_file_line = from_file_lines[from_file_line_num]
    to_file_line = to_file_lines[to_file_line_num]
    assert from_file_line == to_file_line, (
        'Unexpected line difference between %s and %s' % (from_file_line,
                                                          to_file_line))
    line_num_mapping[from_file_line_num] = (to_file_line_num, to_file_line)

  line_num_mapping = {}
  from_file_line_num = 0
  to_file_line_num = 0
  for line in diff_lines:
    # E.g. '--- file1.txt 2019-02-02 17:51:49.000000000 -0800'
    if line.startswith(_DIFF_FROM_FILE_PREFIX) or line.startswith(
        _DIFF_TO_FILE_PREFIX):
      continue

    # E.g. '@@ -1,3 +1,3 @@''
    if line.startswith(_DIFF_RANGE_HEADER_PREFIX):
      matched = _DIFF_RANGE_HEADER_REGEX.match(line)
      if not matched:
        raise RuntimeError(
            'This script doesn\'t understand the diff section header: "%s".' %
            line)

      from_file_diff_section_line_num = int(matched.group(1))
      to_file_diff_section_line_num = int(matched.group(3))
      assert (from_file_diff_section_line_num -
              from_file_line_num == to_file_diff_section_line_num -
              to_file_line_num), 'Inconsistent number of unchanged lines'
      while from_file_line_num < from_file_diff_section_line_num:
        _verify_and_add_unchanged_line(from_file_line_num, from_file_lines,
                                       to_file_line_num, to_file_lines,
                                       line_num_mapping)
        from_file_line_num += 1
        to_file_line_num += 1

      continue

    # E.g. ' unchanged line'.
    if line.startswith(_DIFF_WHITESPACE_LINE_PREFIX):
      _verify_and_add_unchanged_line(from_file_line_num, from_file_lines,
                                     to_file_line_num, to_file_lines,
                                     line_num_mapping)
      from_file_line_num += 1
      to_file_line_num += 1
      continue

    # E.g. '-extra line in the from file'
    if line.startswith(_DIFF_MINUS_LINE_PREFIX):
      from_file_line_num += 1
      continue

    # E.g. '+extra line in the to file'
    if line.startswith(_DIFF_PLUS_LINE_PREFIX):
      to_file_line_num += 1
      continue

  assert (len(from_file_lines) - from_file_line_num == len(to_file_lines) -
          to_file_line_num
         ), 'Inconsistent number of unchanged lines at the end of the files'
  while from_file_line_num < len(from_file_lines):
    _verify_and_add_unchanged_line(from_file_line_num, from_file_lines,
                                   to_file_line_num, to_file_lines,
                                   line_num_mapping)
    from_file_line_num += 1
    to_file_line_num += 1

  assert 0 in line_num_mapping and line_num_mapping[0] == (
      0, 'Manually padded line'), 'A manually padded line is expected to exist'
  del line_num_mapping[0]
  return line_num_mapping
