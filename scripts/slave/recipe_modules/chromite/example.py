# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromite',
]


def RunSteps(api):
  # Basic checkout exercise.
  api.chromite.checkout()
  api.chromite.setup_board('amd64-generic', args=['--cache-dir', '.cache'])
  api.chromite.build_packages('amd64-generic')
  api.chromite.cros_sdk('cros_sdk', ['echo', 'hello'],
                        environ={ 'var1': 'value' })
  api.chromite.cbuildbot('cbuildbot', 'amd64-generic-full',
                         args=['--clobber', '--build-dir', '/here/there'])


def GenTests(api):
  yield api.test('basic')
