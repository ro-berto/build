# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
]

def GenSteps(api):
  config_vals = {}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )

  api.chromium.set_config('chromium', **config_vals)

  api.chromium.c.gyp_env.GYP_DEFINES['linux_strip_binary'] = 1

  s = api.gclient.c.solutions[0]

  USE_MIRROR = api.gclient.c.USE_MIRROR
  def DartRepositoryURL(*pieces):
    BASES = ('https://dart.googlecode.com/svn',
             'svn://svn-mirror.golo.chromium.org/dart')
    return '/'.join((BASES[USE_MIRROR],) + pieces)

  s.url = DartRepositoryURL('branches', 'bleeding_edge', 'deps', 'dartium.deps')
  s.name = 'dartium.deps'
  s.custom_deps = api.properties.get('gclient_custom_deps') or {}
  s.revision = api.properties.get('revision')
  api.gclient.c.got_revision_mapping.pop('src', None)
  api.gclient.c.got_revision_mapping['src/dart'] = 'got_revision'
  if USE_MIRROR:
    s.custom_vars.update({
      'dartium_base': 'svn://svn-mirror.golo.chromium.org'})

  yield api.gclient.checkout()

  # gclient api incorrectly sets Path('[CHECKOUT]') to build/src/dartium.deps
  # because Dartium has its DEPS file in dartium.deps, not directly in src.
  api.path.set_dynamic_path('checkout', api.path.slave_build(('src')))

  yield api.chromium.runhooks()
  yield api.chromium.compile()

  results_dir = api.path.slave_build('layout-test-results')
  test = api.path.build('scripts', 'slave', 'chromium',
                        'layout_test_wrapper.py')
  args = ['--target', api.chromium.c.BUILD_CONFIG,
          '-o', results_dir,
          '--build-dir', api.chromium.c.build_dir]
  yield api.chromium.runtests(test, args, name='webkit_tests')

def GenTests(api):
  for plat in ('win', 'mac', 'linux'):
    for bits in (32, 64):
      for use_mirror in (True, False):
        yield (
          api.test('basic_%s_%s_Mirror%s' % (plat, bits, use_mirror)) +
          api.properties(TARGET_BITS=bits, USE_MIRROR=use_mirror) +
          api.platform(plat, bits)
      )
