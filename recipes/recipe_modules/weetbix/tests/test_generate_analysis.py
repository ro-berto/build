# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for generate_analysis."""
from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'weetbix',
    'recipe_engine/json',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  # This is to get coverage of the test_api which is bein used more extensively
  # outside this module
  api.step.empty('step')


def GenTests(api):
  yield api.test(
      'basic',
      api.step_data(
          'step',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'testVariants': [
                      api.weetbix.generate_analysis(
                          'testA',
                          expected_count=10,
                          unexpected_count=0,
                          examples_times=[0, 1],
                          flaky_verdict_count=1,
                      ),
                  ]
              }))),
      api.post_process(post_process.DropExpectation),
  )
