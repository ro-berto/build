# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'math_utils',
  'recipe_engine/step',
]


def RunSteps(api):
  api.step('results', [])
  api.step.active_result.presentation.logs['details'] = [
    'welchs_t_test (1): %r' % (api.math_utils.welchs_t_test(
        [1, 2, 3], [4, 5, 6]),),
    'welchs_t_test (2): %r' % (api.math_utils.welchs_t_test(
        [1, 1, 1], [2, 2, 2]),),
    'welchs_t_test (3): %r' % (api.math_utils.welchs_t_test(
        [1, 1, 1], [1, 1, 1]),),
    'confidence_score (1): %r' % (api.math_utils.confidence_score(
        [1], [2]),),
    'confidence_score (2): %r' % (api.math_utils.confidence_score(
        [], [], accept_single_bad_or_good=True),),
    'confidence_score (3): %r' % (api.math_utils.confidence_score(
        [1, 2, 3], [4, 5, 6], accept_single_bad_or_good=True),),
    'standard_error (1): %r' % (api.math_utils.standard_error(
        [1]),),
    'standard_error (2): %r' % (api.math_utils.standard_error(
        [1, 2, 3]),),
    'pooled_standard_error (1): %r' % (api.math_utils.pooled_standard_error(
        [[1, 2], [3, 4]]),),
    'pooled_standard_error (2): %r' % (api.math_utils.pooled_standard_error(
        []),),
    'relative_change (1): %r' % (api.math_utils.relative_change(1, 1),),
    'relative_change (2): %r' % (api.math_utils.relative_change(0, 1),),
    'relative_change (3): %r' % (api.math_utils.relative_change(1, 2),),
    'variance (1): %r' % (api.math_utils.variance([1]),),
  ]


def GenTests(api):
  yield api.test('basic')
