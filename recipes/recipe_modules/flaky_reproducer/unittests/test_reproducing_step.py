# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest

from libs import ReproducingStep
from testdata import get_test_data


class ReproducingStepTest(unittest.TestCase):

  def test_from_jsonish(self):
    json_data = json.loads(get_test_data('reproducing_step.json'))
    step = ReproducingStep.from_jsonish(json_data)
    self.assertEqual(step.reproducing_rate, 0.9)
    self.assertEqual(step.duration, 123)
    self.assertEqual(step.debug_info['reproduced_cnt'], 1)
    self.assertEqual(step.debug_info['total_retries'], 30)
    return step

  def test_to_jsonish(self):
    step = self.test_from_jsonish()
    json_data = json.loads(get_test_data('reproducing_step.json'))
    self.assertDictEqual(step.to_jsonish(), json_data)

  def test_readable_info(self):
    self.maxDiff = None
    step = self.test_from_jsonish()
    self.assertEqual(
        step.readable_info(),
        ('This failure could be reproduced (90.0%) with command on'
         ' Windows-11-22000:\n'
         'vpython3 ../../testing/test_env.py ./base_unittests.exe'
         ' --test-launcher-bot-mode --asan=0 --lsan=0 --msan=0 --tsan=0'
         ' --cfi-diag=0 --test-launcher-retry-limit=0 '
         '--isolated-script-test-filter=MockUnitTests.CrashTest'
         ':MockUnitTests.PassTest --isolated-script-test-repeat=3 '
         '--test-launcher-batch-limit=0 --test-launcher-jobs=5'))

  def test_readable_info_not_reproduced(self):
    self.maxDiff = None
    step = self.test_from_jsonish()
    step.reproducing_rate = 0
    self.assertEqual(step.readable_info(),
                     'This failure was NOT reproduced on Windows-11-22000.')

  def test_better_than(self):
    step_50 = ReproducingStep(None, 0.5, 123)
    step_60 = ReproducingStep(None, 0.6, 123)
    step_90 = ReproducingStep(None, 0.9, 12)
    step_92 = ReproducingStep(None, 0.92, 123)
    step_95 = ReproducingStep(None, 0.95, 123)
    self.assertTrue(step_60.better_than(step_50))
    self.assertTrue(step_90.better_than(step_60))
    self.assertTrue(step_90.better_than(step_92))
    self.assertTrue(step_95.better_than(step_90))
