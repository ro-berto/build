# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/buildbucket',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  _, builder_config = api.chromium_tests_builder_config.lookup_builder()
  api.chromium_tests.configure_build(builder_config)
  update_step, _ = api.chromium_tests.prepare_checkout(builder_config)
  api.chromium_tests.deapply_patch(update_step)


def GenTests(api):
  yield api.test(
      'basic',
      api.platform.name('win'),
      api.chromium.try_build(
          builder_group='tryserver.chromium.win',
          builder='win7-rel',
      ),
  )
