# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'path',
  'properties',
  'tryserver',
]


def GenSteps(api):
  api.path.set_dynamic_path('checkout', api.path.slave_build)
  yield api.tryserver.maybe_apply_issue()


def GenTests(api):
  yield (api.test('with_svn_patch') +
    api.properties(patch_url='svn://checkout.url'))

  yield (api.test('with_rietveld_patch') +
    api.properties.tryserver())
