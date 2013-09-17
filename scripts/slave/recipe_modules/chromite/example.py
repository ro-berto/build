# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromite',
  'properties',
]

def GenSteps(api):
  bits = api.properties['TARGET_BITS']
  board = 'x86-generic' if bits == 32 else 'amd64-generic'

  yield (
    api.chromite.checkout(),
    api.chromite.setup_board(board, flags={'cache-dir': '.cache'}),
    api.chromite.build_packages(board),
  )


def GenTests(_api):
  for bits in (32, 64):
    yield 'basic_%s' % bits, {
      'properties': {'TARGET_BITS': bits},
    }
