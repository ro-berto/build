# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for lookup_bug."""

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'weetbix',
    'recipe_engine/assertions',
    'recipe_engine/json',
    'recipe_engine/step',
]


def RunSteps(api):
  with api.step.nest('nest_parent') as presentation:
    bug = 'chromium/123'
    rules = api.weetbix.lookup_bug(bug)
    presentation.logs['rules'] = api.json.dumps(rules)


from recipe_engine import post_process


def GenTests(api):
  yield api.test(
      'base',
      api.weetbix.lookup_bug([
          'projects/chromium/rules/00000000000000000000ffffffffffff',
      ],
                             'chromium/123',
                             parent_step_name='nest_parent'),
      api.post_check(lambda check, steps: check(
          api.json.loads(steps['nest_parent'].logs['rules']) == [
              'projects/chromium/rules/00000000000000000000ffffffffffff',
          ])),
      api.post_process(post_process.DropExpectation),
  )
