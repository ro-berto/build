# Copyright (c) 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/runtime',
    'goma_server',
]


def RunSteps(api):
  repository = 'https://chromium.googlesource.com/infra/goma/server'
  package_base = 'go.chromium.org/goma/server'
  api.goma_server.BuildAndTest(repository, package_base)


def GenTests(api):
  yield (api.test('goma_server_presubmit') +
         api.platform('linux', 64) +
         api.runtime(is_luci=True, is_experimental=False) +
         api.buildbucket.try_build(
             builder='Goma Server Presubmit',
             change_number=4840,
             patch_set=2))
