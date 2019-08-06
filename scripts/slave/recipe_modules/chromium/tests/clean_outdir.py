# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

DEPS = [
  'chromium',
  'depot_tools/gclient',
  'depot_tools/bot_update',
]

def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.bot_update.ensure_checkout()

  raw_result = api.chromium.compile()
  if raw_result.status != common_pb.SUCCESS:
    return raw_result
  api.chromium.clean_outdir()


def GenTests(api):
  yield (
      api.test('basic')
  )

  yield (
    api.test('compile_failure') +
    api.step_data('compile', retcode=1) +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )

