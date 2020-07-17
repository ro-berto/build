# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Exports directory metadata to GCS.

Exports metadata from DIR_METADATA files to Google Storage.
* COMPUTED form: gs://chrome-metadata/metadata_computed.json
* FULL form:     gs://chrome-metadata/metadata_full.json

In legacy format:
* COMPUTED form: gs://chromium-owners/component_map_subdirs.json
* FULL form:     gs://chromium-owners/component_map.json

See more on forms in
https://source.chromium.org/chromium/infra/infra/+/master:go/src/infra/tools/dirmd/proto/mapping.proto
"""

import copy
import re

from RECIPE_MODULES.build import chromium


DEPS = [
    'chromium_tests',
    'depot_tools/depot_tools',
    'recipe_engine/path',
    'recipe_engine/step',
]

DEST_BUCKET = 'chrome-metadata'

def RunSteps(api):
  # Replicate the config of a vanilla linux builder.
  bot_config = api.chromium_tests.create_bot_config_object(
      [chromium.BuilderId.create_for_master('chromium.linux', 'Linux Builder')])
  # configure_build() is required by prepare-checkout
  api.chromium_tests.configure_build(bot_config)
  api.chromium_tests.prepare_checkout(bot_config)

  api.step('dirmd chromium-update', [
    api.path['checkout'].join('third_party', 'depot_tools', 'dirmd'),
    'chromium-update',
    '-chromium-checkout', api.path['checkout'],
    '-bucket', DEST_BUCKET,
    # TODO(crbug.com/1102997): pass -bucket-legacy when we ensure the
    # tool works correctly.
  ])


def GenTests(api):
  yield api.test('basic')
