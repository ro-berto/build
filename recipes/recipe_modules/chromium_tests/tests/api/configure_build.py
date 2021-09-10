# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
]

BUILDERS = ctbc.BuilderDatabase.create({
    'fake.group': {
        'Android Apply Config Builder':
            ctbc.BuilderSpec.create(
                android_config='main_builder_mb',
                chromium_config='chromium',
                gclient_config='chromium',
                test_results_config='public_server',
                android_apply_config=['use_devil_provision'],
            ),
    },
})


def RunSteps(api):
  _, builder_config = (
      api.chromium_tests_builder_config.lookup_builder(builder_db=BUILDERS))
  api.chromium_tests.configure_build(builder_config)


def GenTests(api):
  yield api.test(
      'android_apply_config',
      api.chromium.ci_build(
          builder_group='fake.group', builder='Android Apply Config Builder'),
      api.post_process(post_process.DropExpectation),
  )
