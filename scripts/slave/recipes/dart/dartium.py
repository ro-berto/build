# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
]

PERF_TESTS = [
  'blink_perf.animation',
  'canvasmark',
  'dromaeo.domcoreattr',
  'dromaeo.domcoremodify',
  'dromaeo.domcorequery',
  'dromaeo.domcoretraverse',
  'dromaeo.jslibattrjquery',
  'dromaeo.jslibattrprototype',
  'dromaeo.jslibeventjquery',
  'dromaeo.jslibeventprototype',
  'dromaeo.jslibmodifyjquery',
  'dromaeo.jslibmodifyprototype',
  'dromaeo.jslibstylejquery',
  'dromaeo.jslibstyleprototype',
  'dromaeo.jslibtraversejquery',
  'dromaeo.jslibtraverseprototype',
  'image_decoding.image_decoding_measurement',
  'kraken',
  'octane',
  'pica.pica',
  'spaceport',
  'sunspider',
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

  deps_name = api.properties.get('deps', 'dartium.deps')
  s.url = DartRepositoryURL('branches', 'bleeding_edge', 'deps', deps_name)
  s.name = deps_name
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
  yield api.chromium.runtest(test, args, name='webkit_tests')

  if api.platform.is_linux:
    dashboard_upload_url = 'https://chromeperf.appspot.com'
    build_exe = api.chromium.c.build_dir(api.chromium.c.build_config_fs)
    factory_properties = {
      'blink_config':  'chromium',
      'browser_exe':  str(build_exe('chrome')),
      'build_dir':  'src/out',
      'expectations':  True,
      'halt_on_missing_build':  True,
      'run_reference_build': False,
      'show_perf_results':  True,
      'target':  'Release',
      'target_os':  None,
      'target_platform':  'linux2',
      'tools_dir':  str(api.path.slave_build('src', 'tools')),
    }

    for test in PERF_TESTS:
      factory_properties['test_name'] = test
      factory_properties['step_name'] = test
      fp = "--factory-properties=%s" % json.dumps(factory_properties)
      yield api.chromium.runtest(
          api.chromium.m.path.build('scripts', 'slave', 'telemetry.py'),
          [fp], name=test, python_mode=True,
          results_url=dashboard_upload_url,
          annotate='graphing', perf_dashboard_id=test, test_type=test,
          revision=s.revision,
      )


def GenTests(api):
  for plat in ('win', 'mac', 'linux'):
    for bits in (64,):
      for use_mirror in (True, False):
        yield (
          api.test('basic_%s_%s_Mirror%s' % (plat, bits, use_mirror)) +
          api.properties(
              TARGET_BITS=bits,
              USE_MIRROR=use_mirror,
              perf_id='dartium-linux-release',
              deps='dartium.deps',
              revision='12345') +
          api.platform(plat, bits)
      )
