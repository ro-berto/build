# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Launches the gatekeeper."""

DEPS = [
  'gatekeeper',
  'path',
]


def GenSteps(api):
  api.gatekeeper(
    api.path['build'].join('scripts', 'slave', 'gatekeeper.json'),
    api.path['build'].join('scripts', 'slave', 'gatekeeper_trees.json'),
  )


def GenTests(api):
  yield api.test('basic')
