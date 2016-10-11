#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.path.pardir))

from bisect_tester_staging import perf_test


class MetricTest(unittest.TestCase):  # pragma: no cover

  def test_metric_pair_no_interaction_non_summary(self):
    metric = perf_test.Metric('chart/trace')
    self.assertEqual(('chart', 'trace'), metric.as_pair())

  def test_metric_pair_no_interaction_summary(self):
    metric = perf_test.Metric('chart/chart')
    self.assertEqual(('chart', 'chart'), metric.as_pair())

  def test_metric_pair_with_interaction_not_summary(self):
    metric = perf_test.Metric('chart/interaction/trace')
    self.assertEqual(('interaction@@chart', 'trace'), metric.as_pair())

  def test_metric_pair_with_interaction_not_summary_old_style(self):
    metric = perf_test.Metric('chart/interaction/trace')
    self.assertEqual(
        ('interaction-chart', 'trace'),
        metric.as_pair(perf_test.Metric.OLD_STYLE_DELIMITER))

  def test_metric_pair_invalid_metric_string_no_slashes(self):
    metric = perf_test.Metric('metric-string-with-no-slashes')
    self.assertEqual((None, None), metric.as_pair())

  def test_metric_pair_invalid_metric_string_many_slashes(self):
    metric = perf_test.Metric('metric/string/with/many/slashes')
    self.assertEqual((None, None), metric.as_pair())


class ParseValuesTest(unittest.TestCase):  # pragma: no cover

  def _sample_results(self):
    return {
        'charts': {
            'label@@chart-foo': {
                'http://example.com/bar': {
                    'type': 'list_of_scalar_values',
                    'values': [2.0, 3.0],
                },
                'summary': {
                    'type': 'list_of_scalar_values',
                    'values': [1.0, 2.0, 3.0]
                }
            }
        }
    }

  def test_find_values_three_part_metric(self):
    metric = perf_test.Metric('chart-foo/label/http___example.com_bar')
    results = self._sample_results()
    self.assertEqual((True, [2.5]), perf_test.find_values(results, metric))

  def test_find_values_three_part_metric_old_delimiter(self):
    metric = perf_test.Metric('chart-foo/label/http___example.com_bar')
    results = {
        'charts': {
            'label-chart-foo': {
                'http://example.com/bar': {
                    'type': 'list_of_scalar_values',
                    'values': [2.0, 3.0],
                },
                'summary': {
                    'type': 'list_of_scalar_values',
                    'values': [1.0, 2.0, 3.0]
                }
            }
        }
    }
    self.assertEqual((True, [2.5]), perf_test.find_values(results, metric))

  def test_find_values_two_part_metric_with_dash_in_chart(self):
    metric = perf_test.Metric('label-chart-foo/http___example.com_bar')
    results = self._sample_results()
    self.assertEqual((True, [2.5]), perf_test.find_values(results, metric))

  def test_find_values_summary_metric_with_dash_in_chart(self):
    metric = perf_test.Metric('label-chart-foo/label-chart-foo')
    results = self._sample_results()
    self.assertEqual((True, [2.0]), perf_test.find_values(results, metric))

  def test_find_values_bogus_metric(self):
    metric = perf_test.Metric('chart-baz/trace')
    results = self._sample_results()
    self.assertEqual((False, []), perf_test.find_values(results, metric))



if __name__ == '__main__':
  unittest.main()  # pragma: no cover
