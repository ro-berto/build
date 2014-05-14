# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'gsutil',
  'properties',
  'json',
  'path',
  'python',
]

BUILDERS = {
  'local_test': {
    'recipe_config': 'cronet_builder',
    'run_tests': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
      'REPO_URL': 'https://chromium.googlesource.com/chromium/src.git'
    },
    'custom': {
      'deps_file': '.DEPS.git'
    }
  },
  'Android Cronet Builder (dbg)': {
    'recipe_config': 'cronet_builder',
    'run_tests': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
    },
    'custom': {
      'deps_file': 'DEPS'
    }
  },
  'Android Cronet Builder': {
    'recipe_config': 'cronet_rel',
    'run_tests': False,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    }
  },
}

def GenSteps(api):
  droid = api.chromium_android

  buildername = api.properties['buildername']
  builder_config = BUILDERS.get(buildername, {})
  default_kwargs = {
    'REPO_URL': '/'.join((api.properties.get('repository'),
                          api.properties.get('branch'))),
    'INTERNAL': False,
    'REPO_NAME': api.properties.get('branch'),
    'BUILD_CONFIG': 'Debug'
  }

  kwargs = builder_config.get('kwargs', {})
  droid.configure_from_properties(builder_config['recipe_config'],
      **dict(default_kwargs.items() + kwargs.items()))
  droid.c.set_val(builder_config.get('custom', {}))

  yield droid.init_and_sync()
  yield droid.clean_local_files()
  yield droid.runhooks()
  yield droid.compile()

  revision = api.properties.get('revision')
  cronetdir = api.path['checkout'].join('out', droid.c.BUILD_CONFIG, 'cronet')
  destdir = 'cronet-%s-%s' % (kwargs['BUILD_CONFIG'], revision)
  yield api.gsutil.upload(
      source=cronetdir,
      bucket='chromium-cronet/android',
      dest=destdir,
      args=['-R'],
      name='upload_cronet_package',
      link_name='Cronet package')

  if builder_config['run_tests']:
    yield droid.common_tests_setup_steps()
    install_cmd = api.path['checkout'].join('build',
                                            'android',
                                            'adb_install_apk.py')
    yield api.python('install CronetSample', install_cmd,
        args = ['--apk', 'CronetSample.apk'])
    test_cmd = api.path['checkout'].join('build',
                                         'android',
                                         'test_runner.py')
    yield api.python('test CronetSample', test_cmd,
        args = ['instrumentation', '--test-apk', 'CronetSampleTest'])
    yield droid.common_tests_final_steps()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())

def GenTests(api):
  bot_ids = ['local_test', 'Android Cronet Builder (dbg)',
      'Android Cronet Builder']

  for bot_id in bot_ids:
    props = api.properties(
      buildername=bot_id,
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      repository='svn://svn-mirror.golo.chromium.org/chrome/trunk',
      branch='src',
    )
    yield api.test(_sanitize_nonalpha(bot_id)) + props
