# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium import BuilderId

DEPS = ['recipe_engine/assertions']


def RunSteps(api):
  builder_id = BuilderId.create_for_group('fake-group', 'fake-builder')
  api.assertions.assertEqual(str(builder_id), 'fake-group:fake-builder')


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
