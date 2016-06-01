# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'sync_submodules',
]


def RunSteps(api):
  api.sync_submodules(
      'https://chromium.googlesource.com/chromium/src',
      'https://chromium.googlesource.com/chromium/src/codesearch')
  api.sync_submodules(
      'https://chromium.googlesource.com/infra/infra',
      'https://chromium.googlesource.com/infra/infra/codesearch')


def GenTests(api):
  yield api.test('basic')
