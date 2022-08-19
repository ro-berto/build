# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.engine_types import thaw
from recipe_engine.recipe_api import Property

from PB.go.chromium.org.luci.buildbucket.proto \
  import builder_common as builder_common_pb

PYTHON_VERSION_COMPATIBILITY = 'PY3'

DEPS = [
    'chromium_polymorphic',
    'recipe_engine/assertions',
    'recipe_engine/properties',
]

PROPERTIES = {
    'builder_id': Property(kind=dict),
    'expected_properties': Property(kind=dict),
}


def RunSteps(api, builder_id, expected_properties):
  builder_id = builder_common_pb.BuilderID(**builder_id)
  properties = api.chromium_polymorphic.get_target_properties(builder_id)
  expected_properties = thaw(expected_properties)
  api.assertions.assertEqual(properties, expected_properties)


def GenTests(api):
  builder_id = {
      'project': 'fake-project',
      'bucket': 'fake-bucket',
      'builder': 'fake-builder',
  }

  yield api.test(
      'basic',
      api.chromium_polymorphic.properties_on_target_build({
          'builder_group': 'fake-group',
          '$bootstrap/properties': 'fake-bootstrap-properties',
      }),
      api.properties(
          builder_id=builder_id,
          expected_properties={
              '$build/chromium_polymorphic': {
                  'target_builder_id': builder_id,
                  'target_builder_group': 'fake-group',
              },
              '$bootstrap/properties': 'fake-bootstrap-properties',
          },
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
