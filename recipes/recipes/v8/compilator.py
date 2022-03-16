# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Compilator prototype.
"""


PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
  'recipe_engine/json',
  'recipe_engine/step',
]

# Temporary test data.
swarm_hashes = {
  "bot_default":
    "800df08e7c70a1b55e262c29646b7df8c8a9a9704c9625190cb6d130899536df/319",
}

parent_test_spec = {
  "swarming_dimensions": {
    "cpu": "x86-64-avx2",
    "os": "Ubuntu-18.04"
  },
  "swarming_task_attrs": {},
  "tests": [
    [
      "v8testing", 4, None, "", [], {}, {}
    ]
  ]
}

def RunSteps(api):
  with api.step.nest('build'):
    api.step('generate_build_files', cmd=None)
    api.step('compile', cmd=None)

  trigger_properties = {}
  trigger_properties['swarm_hashes'] = swarm_hashes
  trigger_properties['parent_test_spec'] = parent_test_spec

  properties_step = api.step('swarming trigger properties', [])
  properties_step.presentation.properties[
      'swarming_trigger_properties'] = trigger_properties
  properties_step.presentation.logs[
      'swarming_trigger_properties'] = api.json.dumps(
          trigger_properties, indent=2)

def GenTests(api):
  yield api.test("basic")
