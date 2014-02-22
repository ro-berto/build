# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'v8',
  'platform',
  'properties',
]

def GenSteps(api):
  api.v8.set_config('v8', optional=True)

  yield api.v8.checkout()
  yield api.v8.runhooks()
  yield api.v8.compile()

  # Tests.
  # TODO(machenbach): Implement the tests.

def GenTests(api):
  for bits in [32, 64]:
    for build_config in ['Release', 'Debug']:
      yield (
        api.test('%s%s' % (build_config, bits)) +
        api.properties(build_config=build_config, bits=bits)
      )

  for build_config in ['Release', 'Debug']:
    yield (
      api.test('arm_%s' % build_config) +
      api.properties(build_config=build_config, target_arch='arm')
    )

  yield (
    api.test('mips_target') +
    api.properties(build_config='Release', target_arch='mipsel')
  )

  yield api.test('default_platform') + api.platform('linux', 64)

  yield api.test('clobber') + api.properties(clobber='')
