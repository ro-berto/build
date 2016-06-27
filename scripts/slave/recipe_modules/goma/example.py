# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/platform',
  'goma',
]

def RunSteps(api):
  api.goma.ensure_goma()
  api.goma.start()
  # build something using goma.
  api.goma.stop()


def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    yield api.test(platform) + api.platform.name(platform)
