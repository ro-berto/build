#!/usr/bin/env vpython
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import rebase_git_diff


class RebaseGitDiffTest(unittest.TestCase):

  # This test tests that the scenario that only one file is changed, and the
  # changed lines are all within the same diff section.
  def test_one_file_one_diff_section(self):
    gerrit_diff = ('diff --git a/path/test.txt b/path/test.txt\n'
                   'index 0719398930..4a2b716881 100644\n'
                   '--- a/path/test.txt\n'
                   '+++ b/path/test.txt\n'
                   '@@ -10,2 +10,3 @@\n'
                   ' Line 10\n'
                   '-Line 11\n'
                   '+A different line 11\n'
                   '+A newly added line 12\n')

    # The difference between |local_diff| and |gerrit_diff| is that some other
    # CL added 5 lines before Line 10.
    local_diff = ('diff --git a/path/test.txt b/path/test.txt\n'
                  'index 0719398930..4a2b716881 100644\n'
                  '--- a/path/test.txt\n'
                  '+++ b/path/test.txt\n'
                  '@@ -15,2 +15,3 @@\n'
                  ' Line 10\n'
                  '-Line 11\n'
                  '+A different line 11\n'
                  '+A newly added line 12\n')

    expected_mapping = {
        'path/test.txt': {
            16: (11, 'A different line 11'),
            17: (12, 'A newly added line 12')
        }
    }

    mapping = rebase_git_diff.generate_diff_mapping(
        local_diff.split('\n'), gerrit_diff.split('\n'), ['path/test.txt'])
    self.assertEqual(expected_mapping, mapping)

  def test_one_file_multiple_sections(self):
    gerrit_diff = ('diff --git a/path/test.txt b/path/test.txt\n'
                   'index 0719398930..4a2b716881 100644\n'
                   '--- a/path/test.txt\n'
                   '+++ b/path/test.txt\n'
                   '@@ -10,2 +10,3 @@\n'
                   ' Line 10\n'
                   '-Line 11\n'
                   '+A different line 11\n'
                   '+A newly added line 12\n'
                   '@@ -20,1 +21,1 @@\n'
                   '-Line 20\n'
                   '+A different line 20\n')

    # The difference between |local_diff| and |gerrit_diff| is that some other
    # CL added 5 lines before Line 10.
    local_diff = ('diff --git a/path/test.txt b/path/test.txt\n'
                  'index 0719398930..4a2b716881 100644\n'
                  '--- a/path/test.txt\n'
                  '+++ b/path/test.txt\n'
                  '@@ -15,2 +15,3 @@\n'
                  ' Line 10\n'
                  '-Line 11\n'
                  '+A different line 11\n'
                  '+A newly added line 12\n'
                  '@@ -25,1 +26,1 @@\n'
                  '-Line 20\n'
                  '+A different line 20\n')

    expected_mapping = {
        'path/test.txt': {
            16: (11, 'A different line 11'),
            17: (12, 'A newly added line 12'),
            26: (21, 'A different line 20')
        }
    }

    mapping = rebase_git_diff.generate_diff_mapping(
        local_diff.split('\n'), gerrit_diff.split('\n'), ['path/test.txt'])
    self.assertEqual(expected_mapping, mapping)

  def test_multiple_files_multiple_sections(self):
    gerrit_diff = ('diff --git a/path/test1.txt b/path/test1.txt\n'
                   'index 0719398930..4a2b716881 100644\n'
                   '--- a/path/test1.txt\n'
                   '+++ b/path/test1.txt\n'
                   '@@ -10,2 +10,3 @@\n'
                   ' Line 10\n'
                   '-Line 11\n'
                   '+A different line 11\n'
                   '+A newly added line 12\n'
                   'diff --git a/path/test2.txt b/path/test2.txt\n'
                   'index 0719398930..4a2b716881 100644\n'
                   '--- a/path/test2.txt\n'
                   '+++ b/path/test2.txt\n'
                   '@@ -10,2 +10,3 @@\n'
                   ' Line 10\n'
                   '-Line 11\n'
                   '+A different line 11\n'
                   '+A newly added line 12\n'
                   '@@ -20,1 +21,1 @@\n'
                   '-Line 20\n'
                   '+A different line 20\n')

    # The difference between |local_diff| and |gerrit_diff| is that some other
    # CL added 5 lines before Line 10 in both files.
    local_diff = ('diff --git a/path/test1.txt b/path/test1.txt\n'
                  'index 0719398930..4a2b716881 100644\n'
                  '--- a/path/test1.txt\n'
                  '+++ b/path/test1.txt\n'
                  '@@ -15,2 +15,3 @@\n'
                  ' Line 10\n'
                  '-Line 11\n'
                  '+A different line 11\n'
                  '+A newly added line 12\n'
                  'diff --git a/path/test2.txt b/path/test2.txt\n'
                  'index 0719398930..4a2b716881 100644\n'
                  '--- a/path/test2.txt\n'
                  '+++ b/path/test2.txt\n'
                  '@@ -15,2 +15,3 @@\n'
                  ' Line 10\n'
                  '-Line 11\n'
                  '+A different line 11\n'
                  '+A newly added line 12\n'
                  '@@ -25,1 +26,1 @@\n'
                  '-Line 20\n'
                  '+A different line 20\n')

    expected_mapping = {
        'path/test1.txt': {
            16: (11, 'A different line 11'),
            17: (12, 'A newly added line 12')
        },
        'path/test2.txt': {
            16: (11, 'A different line 11'),
            17: (12, 'A newly added line 12'),
            26: (21, 'A different line 20')
        }
    }

    mapping = rebase_git_diff.generate_diff_mapping(
        local_diff.split('\n'), gerrit_diff.split('\n'),
        ['path/test1.txt', 'path/test2.txt'])

    self.assertEqual(expected_mapping, mapping)

  # This test tests that the rebase function correctly handles newlines in all
  # following 3 scerios:
  # 1. If a newline is added, the diff is: '+\n'.
  # 2. If a newline is unchanged, the diff is: '\n'. (without prefix whitespace)
  # 3. If a newline is deleted, the diff is: '-\n'.
  def test_new_line_behaviors(self):
    gerrit_diff = ('diff --git a/path/test.txt b/path/test.txt\n'
                   'index 0719398930..4a2b716881 100644\n'
                   '--- a/path/test.txt\n'
                   '+++ b/path/test.txt\n'
                   '@@ -10,3 +10,4 @@\n'
                   ' Line 10\n'
                   '\n'
                   '-\n'
                   '+A different line 11\n'
                   '+\n')

    # The difference between |local_diff| and |gerrit_diff| is that some other
    # CL added 5 lines before Line 10.
    local_diff = ('diff --git a/path/test.txt b/path/test.txt\n'
                  'index 0719398930..4a2b716881 100644\n'
                  '--- a/path/test.txt\n'
                  '+++ b/path/test.txt\n'
                  '@@ -15,3 +15,4 @@\n'
                  ' Line 10\n'
                  '\n'
                  '-\n'
                  '+A different line 11\n'
                  '+\n')

    expected_mapping = {
        'path/test.txt': {
            17: (12, 'A different line 11'),
            18: (13, '')
        }
    }

    mapping = rebase_git_diff.generate_diff_mapping(
        local_diff.split('\n'), gerrit_diff.split('\n'), ['path/test.txt'])
    self.assertEqual(expected_mapping, mapping)

  # This test tests the behaviors of the sources arguments to specify list of
  # files to get diff mapping for.
  def test_filter_source_files(self):
    gerrit_diff = ('diff --git a/path/test1.txt b/path/test1.txt\n'
                   'index 0719398930..4a2b716881 100644\n'
                   '--- a/path/test1.txt\n'
                   '+++ b/path/test1.txt\n'
                   '@@ -10,2 +10,3 @@\n'
                   ' Line 10\n'
                   '-Line 11\n'
                   '+A different line 11\n'
                   '+A newly added line 12\n'
                   'diff --git a/path/test2.txt b/path/test2.txt\n'
                   'index 0719398930..4a2b716881 100644\n'
                   '--- a/path/test2.txt\n'
                   '+++ b/path/test2.txt\n'
                   '@@ -20,1 +21,1 @@\n'
                   '-Line 20\n'
                   '+A different line 20\n')

    # The difference between |local_diff| and |gerrit_diff| is that some other
    # CL added 5 lines before Line 10 in both files.
    local_diff = ('diff --git a/path/test1.txt b/path/test1.txt\n'
                  'index 0719398930..4a2b716881 100644\n'
                  '--- a/path/test1.txt\n'
                  '+++ b/path/test1.txt\n'
                  '@@ -15,2 +15,3 @@\n'
                  ' Line 10\n'
                  '-Line 11\n'
                  '+A different line 11\n'
                  '+A newly added line 12\n'
                  'diff --git a/path/test2.txt b/path/test2.txt\n'
                  'index 0719398930..4a2b716881 100644\n'
                  '--- a/path/test2.txt\n'
                  '+++ b/path/test2.txt\n'
                  '@@ -25,1 +26,1 @@\n'
                  '-Line 20\n'
                  '+A different line 20\n')

    expected_mapping = {
        'path/test1.txt': {
            16: (11, 'A different line 11'),
            17: (12, 'A newly added line 12')
        }
    }

    mapping = rebase_git_diff.generate_diff_mapping(
        local_diff.split('\n'), gerrit_diff.split('\n'), ['path/test1.txt'])

    self.assertEqual(expected_mapping, mapping)


if __name__ == '__main__':
  unittest.main()
