# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'binary_size',
    'recipe_engine/properties',
]


def RunSteps(api):
  return api.binary_size.fuchsia_binary_size(
      chromium_config='chromium',
      chromium_apply_configs=['mb'],
      gclient_config='chromium',
      gclient_apply_configs=['fuchsia_arm64'])


def GenTests(api):
  yield api.test('basic', api.binary_size.build(),
                 api.post_process(post_process.StatusSuccess),
                 api.post_process(post_process.DropExpectation))
