# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common steps for recipes that sync/build Cronet sources."""

from recipe_engine.types import freeze
from recipe_engine import recipe_api

class CronetApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(CronetApi, self).__init__(**kwargs)
    self._repo_path = None

  INSTRUMENTATION_TESTS = freeze([
    {
      'target': 'cronet_sample_test_apk',
    },
    {
      'target': 'cronet_smoketests_missing_native_library_instrumentation_apk',
    },
    {
      'target': 'cronet_smoketests_platform_only_instrumentation_apk',
    },
    {
      'target': 'cronet_test_instrumentation_apk',
    },
  ])

  UNIT_TESTS = freeze([
    'cronet_unittests',
    'net_unittests',
  ])

  DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'

  def init_and_sync(self, recipe_config, kwargs, gyp_defs,
                    chromium_apply_config=None):
    default_kwargs = {
      'REPO_URL': 'https://chromium.googlesource.com/chromium/src',
      'INTERNAL': False,
      'REPO_NAME': 'src',
      'BUILD_CONFIG': 'Debug'
    }
    droid = self.m.chromium_android
    droid.configure_from_properties(
        recipe_config,
        **dict(default_kwargs.items() + kwargs.items()))
    droid.apply_config('use_devil_provision')
    self.m.chromium.apply_config('cronet_builder')
    for c in chromium_apply_config or []:
      self.m.chromium.apply_config(c)
    self.m.chromium.c.gyp_env.GYP_DEFINES.update(gyp_defs)
    droid.init_and_sync(use_bot_update=True)


  def build(self, use_revision=True, use_goma=True):
    if use_goma:
      self.m.chromium.ensure_goma()
    self.m.chromium.runhooks()
    if self.m.chromium.c.project_generator.tool == 'gn': # pragma: no cover
      assert (self.m.chromium.c.HOST_PLATFORM == 'linux'
              and self.m.chromium.c.HOST_BITS == 64)
      self.m.chromium.run_gn(
          use_goma=use_goma,
          gn_path=self.m.path['checkout'].join('buildtools', 'linux64', 'gn'))
    elif self.m.chromium.c.project_generator.tool == 'mb':
      self.m.chromium.run_mb(
          self.m.properties['mastername'],
          self.m.properties['buildername'],
          use_goma=use_goma)
    self.m.chromium.compile(use_goma_module=use_goma)


  def get_version(self):
    version = self.m.chromium.get_version()
    return "%s.%s.%s.%s" % (version['MAJOR'], version['MINOR'],
                            version['BUILD'], version['PATCH'])


  def upload_package(self, build_config, cronetdir=None, platform='android'):
    cronetdir = cronetdir or self.m.path['checkout'].join(
        'out', self.m.chromium_android.c.BUILD_CONFIG, 'cronet')
    destdir = self.get_version() + '/' + build_config
    # Upload cronet version first to ensure that destdir is created.
    self.m.gsutil.upload(
        source=cronetdir.join('VERSION'),
        bucket='chromium-cronet/%s' % platform,
        dest=destdir + '/VERSION',
        name='upload_cronet_version',
        link_name='Cronet version')
    self.m.gsutil.upload(
        source=cronetdir,
        bucket='chromium-cronet/%s' % platform,
        dest=destdir,
        args=['-R'],
        name='upload_cronet_package',
        link_name='Cronet package')


  def sizes(self, perf_id):
    # Measures native .so size.
    self.m.chromium.sizes(results_url=self.DASHBOARD_UPLOAD_URL,
                          perf_id=perf_id, platform='android-cronet')
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      # Track apk metrics.
      self.m.chromium_android.resource_sizes(
              self.m.chromium.output_dir.join('apks', 'CronetSample.apk'),
              chartjson_file=True,
              perf_id=perf_id)


  def run_tests(
      self, build_config, unit_tests=UNIT_TESTS,
      instrumentation_tests=INSTRUMENTATION_TESTS):
    droid = self.m.chromium_android
    checkout_path = self.m.path['checkout']
    droid.common_tests_setup_steps()
    with self.m.step.defer_results():
      for suite in unit_tests:
        droid.run_test_suite(suite, shard_timeout=180)
      for suite in instrumentation_tests:
        droid.run_instrumentation_suite(
            name=suite['target'],
            verbose=True,
            wrapper_script_suite_name=suite['target'],
            num_retries=0,
            result_details=True,
            **suite.get('kwargs', {}))
      droid.common_tests_final_steps()
