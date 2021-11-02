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
https://source.chromium.org/chromium/infra/infra/+/main:go/src/infra/tools/dirmd/proto/mapping.proto
"""



PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'build/chromium',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/step',
]

DEST_BUCKET = 'chrome-metadata'
DEST_BUCKET_LEGACY = 'chromium-owners'

def RunSteps(api):
  api.gclient.set_config('chromium')
  # TODO(gbeaty) This config causes a hook to be executed that updates the clang
  # coverage tools, it's probably unnecessary, but preserves the behavior from
  # when this recipe was relying on the config for Linux Builder
  api.gclient.apply_config('use_clang_coverage')
  with api.context(cwd=api.path['cache'].join('builder')):
    api.bot_update.ensure_checkout()
  # TODO(gbeaty) If none of the hooks are downloading directories containing
  # DIR_METADATA files, then it shouldn't be necessary to run the hooks as part
  # of this recipe
  api.chromium.set_config('chromium')
  api.chromium.runhooks()

  api.step('dirmd chromium-update', [
    api.path['checkout'].join('third_party', 'depot_tools', 'dirmd'),
    'chromium-update',
    '-chromium-checkout', api.path['checkout'],
    '-bucket', DEST_BUCKET,
    '-bucket-legacy', DEST_BUCKET_LEGACY,
  ])


def GenTests(api):
  yield api.test('basic')
