# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common steps for recipes that sync/build Cronet sources."""

import sys

from recipe_engine import recipe_api
from recipe_engine.engine_types import freeze
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium


class CronetApi(recipe_api.RecipeApi):

  def __init__(self, **kwargs):
    super(CronetApi, self).__init__(**kwargs)
    self._repo_path = None

  DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'

  def init_and_sync(self, recipe_config, kwargs, chromium_apply_config=None):
    default_kwargs = {
        'REPO_URL': 'https://chromium.googlesource.com/chromium/src',
        'INTERNAL': False,
        'REPO_NAME': 'src',
        'BUILD_CONFIG': 'Debug'
    }
    droid = self.m.chromium_android
    default_kwargs.update(kwargs)
    droid.configure_from_properties(recipe_config, **default_kwargs)
    droid.apply_config('use_devil_provision')
    self.m.chromium.apply_config('cronet_builder')
    for c in chromium_apply_config or []:
      self.m.chromium.apply_config(c)
    droid.init_and_sync(use_bot_update=True)

  def build(self,
            builder_id=None,
            targets=None,
            use_goma=True,
            use_reclient=False):
    builder_id = builder_id or self.m.chromium.get_builder_id()
    if use_goma:
      self.m.chromium.ensure_goma()
    self.m.chromium.runhooks()
    if self.m.chromium.c.project_generator.tool == 'gn':  # pragma: no cover
      assert (self.m.chromium.c.HOST_PLATFORM == 'linux' and
              self.m.chromium.c.HOST_BITS == 64)
      gn_path = self.m.path['checkout'].join('buildtools', 'linux64', 'gn')
      if not self.m.path.exists(gn_path):
        gn_path = self.m.path['checkout'].join('third_party', 'gn', 'gn')
      self.m.chromium.run_gn(
          use_goma=use_goma, use_reclient=use_reclient, gn_path=gn_path)
    elif self.m.chromium.c.project_generator.tool == 'mb':
      self.m.chromium.mb_gen(
          builder_id, use_goma=use_goma, use_reclient=use_reclient)
    return self.m.chromium.compile(
        targets=targets, use_goma_module=use_goma, use_reclient=use_reclient)

  def get_version(self):
    version = self.m.chromium.get_version()
    return "%s.%s.%s.%s" % (version['MAJOR'], version['MINOR'],
                            version['BUILD'], version['PATCH'])

  def get_bucket(self, platform):
    if self.m.runtime.is_experimental:
      return 'chromium-cronet/experimental/%s' % platform
    return 'chromium-cronet/%s' % platform

  def upload_package(self, build_config, cronetdir=None, platform='android'):
    cronetdir = cronetdir or self.m.path['checkout'].join(
        'out', self.m.chromium_android.c.BUILD_CONFIG, 'cronet')
    destdir = self.get_version() + '/' + build_config
    # Upload cronet version first to ensure that destdir is created.
    self.m.gsutil.upload(
        source=cronetdir.join('VERSION'),
        bucket=self.get_bucket(platform),
        dest=destdir + '/VERSION',
        name='upload_cronet_version',
        link_name='Cronet version')
    self.m.gsutil.upload(
        source=cronetdir,
        bucket=self.get_bucket(platform),
        dest=destdir,
        args=['-R'],
        name='upload_cronet_package',
        link_name='Cronet package')

  def sizes(self, perf_builder_name_alias):
    # Don't track sizes on experimental bots.
    if self.m.runtime.is_experimental:
      return
    # Measures native .so size.
    self.m.chromium.sizes(
        results_url=self.DASHBOARD_UPLOAD_URL,
        perf_builder_name_alias=perf_builder_name_alias,
        platform='android-cronet')
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      # Track apk metrics.
      self.m.chromium_android.resource_sizes(
          self.m.chromium.output_dir.join('apks', 'CronetSample.apk'),
          chartjson_file=True,
          perf_builder_name_alias=perf_builder_name_alias)

  def run_perf_tests(self, perf_builder_name_alias):
    # Don't track performance on experimental bots.
    if self.m.runtime.is_experimental:
      return
    # Before running the perf test, build quic_server and quic_client for this
    # host machine.
    self.m.chromium.set_config('chromium')

    # Make sure not to clobber all the Cronet binaries that were just built.
    # Landmines are very target dependent so they'll likely be different
    # between android and linux, so running runhooks now would make them go off.
    # Prevent clobbering by clearing landmines that would otherwise go off
    # when runhooks is run.It's safe to ignore landmines now because we just
    # did a clobber build.
    self.m.python.inline(
        'clear landmines',
        """
        import subprocess, sys
        proc = subprocess.Popen(
            sys.argv[1], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        with open(sys.argv[2], 'w') as f:
          f.writelines(out)
        """,
        args=[
            self.m.path['checkout'].join('build', 'get_landmines.py'),
            self.m.path['checkout'].join('.landmines')
        ])
    raw_result = self.build(
        targets=['quic_server'],
        builder_id=chromium.BuilderId.create_for_group('chromium.linux',
                                                       'Linux Builder'))
    if raw_result.status != common_pb.SUCCESS:
      return raw_result

    data_dir = self.m.path.mkdtemp('perf_data')
    args = ['--output-format', 'histograms', '--output-dir', data_dir]
    self.m.python(
        'performance test',
        self.m.path['checkout'].join('components', 'cronet', 'android', 'test',
                                     'javaperftests', 'run.py'),
        args=args)

    oauth_token = self.m.puppet_service_account.get_access_token('cronet-perf')

    args = [
        '--results-file',
        data_dir.join('histograms.json'),
        # We are passing this in solely to have the output show up as a link
        # in the step log, it will not be used after the upload is complete.
        '--oauth-token-file',
        self.m.json.input(oauth_token),
        '--perf-builder-name-alias',
        perf_builder_name_alias,
        '--results-url',
        self.DASHBOARD_UPLOAD_URL,
        '--name',
        'cronet_perf_tests',
        '--output-json-file',
        self.m.json.output(),
        '--buildername',
        self.m.buildbucket.builder_name,
        '--buildnumber',
        self.m.buildbucket.build.number,
        '--chromium-checkout-dir',
        self.m.path['start_dir'],
        '--build-dir',
        self.m.chromium.c.build_dir,
        '--send-as-histograms',
    ]

    if 'got_revision_cp' in self.m.properties:
      args.extend(['--got-revision-cp', self.m.properties['got_revision_cp']])
    if 'git_revision' in self.m.properties:
      args.extend(['--git-revision', self.m.properties['git_revision']])

    self.m.build.python(
        'Perf Dashboard Upload',
        self.m.chromium.repo_resource('recipes',
                                      'upload_perf_dashboard_results.py'),
        args,
        step_test_data=(lambda: self.m.json.test_api.output(
            'chromeperf.appspot.com', name='dashboard_url') + self.m.json.
                        test_api.output({})))
