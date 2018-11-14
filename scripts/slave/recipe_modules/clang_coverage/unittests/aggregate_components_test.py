#!/usr/bin/env vpython
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import math
import os
import sys
import unittest

import mock

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(
    0, os.path.abspath(os.path.join(_THIS_DIR, os.pardir, 'resources')))

import generate_coverage_metadata


class AggregateComponentsTest(unittest.TestCase):

  def setUp(self):
    super(AggregateComponentsTest, self).setUp()
    self.maxDiff = None

  @staticmethod
  def make_summary(functions):
    regions = functions * 2
    lines = regions * 10
    result = {
        'lines': {
            'covered': lines,
            'count': int(math.ceil(lines * 1.1))
        },
        'functions': {
            'covered': functions,
            'count': functions + 1,
        },
        'regions': {
            'covered': regions,
            'count': regions + 1,
        },
    }
    return result

  def test_aggregate_summaries(self):
    data = [
        {
            # Ignored in this test.
            'segments': [[1, 2, 3, True, True]],
            'summary': self.make_summary(3),
            'filename': '/b/src/path/to/resource.cc',
        },
        {
            # Ignored in this test.
            'segments': [[1, 2, 3, True, True]],
            'summary': self.make_summary(4),
            'filename': '/b/src/unrelated/resource.cc',
        },
        {
            # Ignored in this test.
            'segments': [[1, 2, 3, True, True]],
            'summary': self.make_summary(10),
            'filename': '/b/src/path/to/nested/file.cc',
        },
        {
            # Ignored in this test.
            'segments': [[1, 2, 3, True, True]],
            'summary': self.make_summary(5),
            'filename': '/b/src/path/to/other_resource.cc',
        },
        {
            # Ignored in this test.
            'segments': [[1, 2, 3, True, True]],
            'summary': self.make_summary(5),
            'filename': '/b/src/path/in_parent.cc',
        },
        {
            # Ignored in this test.
            'segments': [[1, 2, 3, True, True]],
            'summary': self.make_summary(6),
            'filename': '/b/src/file_in_root.cc',
        }
    ]
    mapping = {
        'path': 'parent>component',
        'path/to': 'child>component',
        'path/to/nested': 'grandchild>component'
    }
    dir_summaries = {}
    for entry in data:
      generate_coverage_metadata._add_file_to_directory_summary(
          dir_summaries, '/b/src/', entry)
    component_summaries = generate_coverage_metadata._aggregate_dirs_and_components(
        dir_summaries, mapping)
    # HACK: Make this assertFalse, to examine output, or assertEqual to {} for
    # formatted output.
    self.assertTrue({
        'files': [],
        'components': component_summaries.values(),
        'dirs': dir_summaries.values()
    })


if __name__ == '__main__':
  unittest.main()
