# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'v8',
]

def GenSteps(api):
  yield api.v8.checkout()
  yield api.v8.runhooks()
  yield api.v8.compile()

  # Tests.
  # TODO(machenbach): Implement the tests.

def GenTests(api):
  for bits in [32, 64]:
    for build_config in ['Release', 'Debug']:
      yield '%s%s' % (build_config, bits), {
        'properties': {
          'build_config': build_config,
          'bits': bits,
        },
      }

  for build_config in ['Release', 'Debug']:
    yield 'arm_%s' % (build_config), {
      'properties': {
        'build_config': build_config,
        'target_arch': 'arm',
      },
  }

  yield 'default_platform', {
    'mock': {
      'platform': {
        'name': 'linux',
        'bits': 64,
      }
    },
  }

  yield 'clobber', {
    'properties': {
      'clobber': '',
    },
  }

