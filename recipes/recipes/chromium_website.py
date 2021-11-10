# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.
"""Recipe for building and deploying the www.chromium.org static website."""

from recipe_engine.post_process import DropExpectation
from recipe_engine.recipe_api import Property

from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

from RECIPE_MODULES.depot_tools.gclient import CONFIG_CTX

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/runtime',
    'recipe_engine/step',
]


def RunSteps(api):
  api.gclient.set_config('chromium_website')
  with api.context(cwd=api.path['cache'].join('builder')):
    api.bot_update.ensure_checkout()
  api.gclient.runhooks()

  with api.context(cwd=api.m.path['checkout']):
    npmw_path = api.m.path['checkout'].join('npmw')
    api.step('build', [npmw_path, 'build'])

  return result_pb2.RawResult(
      status=common_pb.SUCCESS,
      summary_markdown="Built chromium website",
  )

def GenTests(api):
  yield api.test(
      'runs',
      api.post_process(DropExpectation),
  )

@CONFIG_CTX()
def chromium_website(c):
  s = c.solutions.add()
  s.name = 'chromium_website'
  s.url = 'https://chromium.googlesource.com/website.git'
