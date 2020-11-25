# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'skylab',
]

from google.protobuf import duration_pb2
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2


def RunSteps(api):
  responses = api.skylab.wait_on_suites("", timeout_seconds=3600)
  api.assertions.assertEqual(len(responses), 0)


def GenTests(api):
  yield api.test('basic')
