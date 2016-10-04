# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/cipd',
  'gae_sdk',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/python',
]


def RunSteps(api):
  api.cipd.install_client()

  for plat in api.gae_sdk.platforms:
    out = api.path['build'].join('gae_sdk', '%s_%s' % (plat, api.platform.name))
    try:
      api.gae_sdk.fetch(plat, out)
    except api.gae_sdk.PackageNotFound as e:
      api.python.failing_step('Failed to fetch', 'No %s package for %s / %s' % (
          plat, api.platform.name, api.platform.bits))


def GenTests(api):
  yield (
      api.test('win') +
      api.platform('win', 64))

  yield (
      api.test('linux') +
      api.platform('linux', 64))

  yield (
      api.test('mac') +
      api.platform('mac', 64))
