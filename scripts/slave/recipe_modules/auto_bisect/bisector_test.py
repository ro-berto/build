#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
import os
import sys
import unittest

root_dir = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir,
    os.path.pardir, os.path.pardir, os.path.pardir))
sys.path.insert(0, os.path.join(root_dir, 'third_party', 'mock-1.0.1'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.path.pardir))

import mock

from auto_bisect.bisector import Bisector



class MockRevisionClass(object):  # pragma: no cover

  def __init__(self, rev_string, bisector):
    self.commit_pos = int(rev_string)
    self.revision_string = rev_string
    self.bisector = bisector
    self.previous_revision = None
    self.next_revision = None
    self.values = []
    self.deps = {}
    self.commit_hash = ''
    self.status = ''

  def get_next_url(self):
    if self.in_progress:
      return 'mockurl'
    return None

  def read_deps(self, tester_name):
    pass

  def get_buildbot_locator(self):
    return {}


@mock.patch.object(Bisector, 'ensure_sync_master_branch', mock.MagicMock())
class BisectorTest(unittest.TestCase):  # pragma: no cover

  def setUp(self):
    self.bisect_config = {
        'test_type': 'perf',
        'command': ('tools/perf/run_benchmark -v '
                    '--browser=release page_cycler.intl_ar_fa_he'),
        'good_revision': '306475',
        'bad_revision': '306478',
        'metric': 'warm_times/page_load_time',
        'repeat_count': '2',
        'max_time_minutes': '5',
        'bug_id': '425582',
        'gs_bucket': 'chrome-perf',
        'builder_host': 'master4.golo.chromium.org',
        'builder_port': '8341',
        'dummy_builds': True,
    }
    self.dummy_api = mock.MagicMock()

  def test_improvement_direction_default(self):
    # By default, no improvement direction should be set
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    self.assertIsNone(bisector.improvement_direction)

  def test_improvement_direction_greater_is_better_fail(self):
    # Improvement up, bad > good: should fail
    self.bisect_config['improvement_direction'] = 1
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    bisector.good_rev.mean_value = 10
    bisector.bad_rev.mean_value = 100
    self.assertFalse(bisector.check_improvement_direction())
    self.assertIn('direction of improvement', ''.join(bisector.warnings))

  def test_improvement_direction_greater_is_better_pass(self):
    # Improvement up, bad < good: should not fail
    self.bisect_config['improvement_direction'] = 1
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    bisector.good_rev.mean_value = 100
    bisector.bad_rev.mean_value = 10
    self.assertTrue(bisector.check_improvement_direction())
    self.assertNotIn('direction of improvement', ''.join(bisector.warnings))

  def test_improvement_direction_lower_is_better_fail(self):
    # Improvement down, bad < good: should fail
    self.bisect_config['improvement_direction'] = -1
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    bisector.good_rev.mean_value = 100
    bisector.bad_rev.mean_value = 10
    self.assertFalse(bisector.check_improvement_direction())
    self.assertIn('direction of improvement', ''.join(bisector.warnings))

  def test_improvement_direction_lower_is_better_pass(self):
    # Improvement down, bad > good: should not fail
    self.bisect_config['improvement_direction'] = -1
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    bisector.good_rev.mean_value = 10
    bisector.bad_rev.mean_value = 100
    self.assertTrue(bisector.check_improvement_direction())
    self.assertNotIn('direction of improvement', ''.join(bisector.warnings))

  def test_improvement_direction_return_code(self):
    # Good revision is bad or bad revision is good, should fail.
    bisect_config = copy.deepcopy(self.bisect_config)
    bisect_config['test_type'] = 'return_code'
    bisector = Bisector(self.dummy_api, bisect_config, MockRevisionClass)
    bisector.good_rev.mean_value = 1
    bisector.bad_rev.mean_value = 0
    self.assertTrue(bisector.is_return_code_mode())
    self.assertFalse(bisector.check_improvement_direction())
    self.assertIn('return code', ''.join(bisector.warnings))

  def test_check_initial_confidence_zero(self):
    # A confidence score of 0 should not satisfy any default.
    mock_score = self.dummy_api.m.math_utils.confidence_score
    mock_score.return_value = 0
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    # The initial confidence check may only apply if there are some values.
    bisector.good_rev.values = [3, 3, 3, 3, 3, 3]
    bisector.bad_rev.values = [3, 3, 3, 3, 3, 3]
    self.assertFalse(bisector.check_initial_confidence())
    self.assertTrue(bisector.failed_initial_confidence)

  def test_check_initial_confidence_one_hundred(self):
    # A confidence score of 100 should satisfy any default.
    mock_score = self.dummy_api.m.math_utils.confidence_score
    mock_score.return_value = 100
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    self.assertTrue(bisector.check_initial_confidence())
    self.assertFalse(bisector.failed_initial_confidence)

  def test_check_initial_confidence_not_required(self):
    # When confidence is not required, confidence_score should not be called.
    mock_score = self.dummy_api.m.math_utils.confidence_score
    self.bisect_config['required_initial_confidence'] = None
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    self.assertTrue(bisector.check_initial_confidence())
    self.assertFalse(mock_score.called)

  def test_check_initial_confidence_fail(self):
    mock_score = self.dummy_api.m.math_utils.confidence_score
    self.bisect_config['required_initial_confidence'] = 99
    # A confidence score of 98.5 should not satisfy the required 99.
    mock_score.return_value = 98.5
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    # The initial confidence check may only apply if there are some values.
    bisector.good_rev.values = [3, 3, 3, 3, 3, 3]
    bisector.bad_rev.values = [3, 3, 3, 3, 3, 3]
    self.assertFalse(bisector.check_initial_confidence())
    self.assertTrue(bisector.failed_initial_confidence)

  def test_check_initial_confidence_pass(self):
    mock_score = self.dummy_api.m.math_utils.confidence_score
    self.bisect_config['required_initial_confidence'] = 99
    # A confidence score of 99.5 should satisfy the required 99.
    mock_score.return_value = 99.5
    bisector = Bisector(self.dummy_api, self.bisect_config, MockRevisionClass)
    # The initial confidence check may only apply if there are some values.
    bisector.good_rev.values = [3, 3, 3, 3, 3, 3]
    bisector.bad_rev.values = [3, 3, 3, 3, 3, 3]
    self.assertTrue(bisector.check_initial_confidence())
    self.assertFalse(bisector.failed_initial_confidence)


if __name__ == '__main__':
  unittest.main()  # pragma: no cover
