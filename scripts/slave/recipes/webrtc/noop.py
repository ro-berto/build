# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/properties',
]

def RunSteps(api):
  pass


def GenTests(api):
  yield (
      api.test('noop') +
      api.properties.tryserver(mastername='tryserver.webrtc',
                               buildername='noop'))
