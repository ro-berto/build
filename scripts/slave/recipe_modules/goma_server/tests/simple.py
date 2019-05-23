# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/buildbucket',
  'goma_server',
]


def RunSteps(api):
  api.goma_server.BuildAndTest(
      'git://goma-server/',
      'goma-server',
      ['/home/goma'],
      allow_diff=False)


def GenTests(api):
  yield (api.test('simple') +
         api.buildbucket.try_build(
             builder='Goma Server Trusty Presubmit',
             change_number=4840,
             patch_set=2))


