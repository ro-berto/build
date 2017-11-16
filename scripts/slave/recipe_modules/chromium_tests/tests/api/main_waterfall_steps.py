# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
]


def RunSteps(api):
  api.chromium_tests.main_waterfall_steps()


def GenTests(api):
  yield (
      api.test('builder') +
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder'}]) +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Builder') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.override_step_data('trigger', stdout=api.raw_io.output_text("""
        {
          "builds":[{
           "status": "SCHEDULED",
           "created_ts": "1459200369835900",
           "bucket": "user.username",
           "result_details_json": "null",
           "status_changed_ts": "1459200369835930",
           "created_by": "user:username@example.com",
           "updated_ts": "1459200369835940",
           "utcnow_ts": "1459200369962370",
           "parameters_json": "{\\"This_has_been\\": \\"removed\\"}",
           "id": "9016911228971028736"
          }],
          "kind": "buildbucket#resourcesItem",
          "etag": "\\"8uCIh8TRuYs4vPN3iWmly9SJMqw\\""
        }
      """))
  )

  yield (
      api.test('builder_on_buildbot') +
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder'}]) +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Builder')
  )

  yield (
      api.test('tester') +
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Tests'}]) +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          parent_buildername='Linux Builder') +
      api.override_step_data(
          'read test spec (chromium.linux.json)',
          api.json.output({
              'Linux Tests': {
                  'gtest_tests': ['base_unittests'],
              },
          })
      )
  )
