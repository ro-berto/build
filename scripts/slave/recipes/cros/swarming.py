# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromite',
  'depot_tools/gitiles',
  'recipe_engine/properties',
]


def RunSteps(api):
  # We have no configuration, except what's received from buildbucket.
  api.chromite.configure({}, {})

  # Fetch chromite and pinned depot tools.
  api.chromite.checkout_chromite()

  # Update or install goma client via cipd.
  api.chromite.m.goma.ensure_goma()

  # Use the system python, not "bundled python" so that we have access
  # to system python packages.
  with api.chromite.with_system_python():
    api.chromite.run()


def GenTests(api):
  #
  # master.chromiumos.chromium
  #

  # Test a minimal invocation.
  yield (
      api.test('swarming_builder')
      + api.properties(
          bot_id='test',
          path_config='generic',
          cbb_config='swarming-build-config',
      )
  )

