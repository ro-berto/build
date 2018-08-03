# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from . import builders


class LibyuvApi(recipe_api.RecipeApi):
  BUILDERS = builders.BUILDERS
  RECIPE_CONFIGS = builders.RECIPE_CONFIGS

  def __init__(self, **kwargs):
    super(LibyuvApi, self).__init__(**kwargs)

  def apply_bot_config(self, builders, recipe_configs, perf_config=None):
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = builders.get(mastername, {})
    self.master_config = master_dict.get('settings', {})

    self.bot_config = master_dict.get('builders', {}).get(buildername)
    assert self.bot_config, ('Unrecognized builder name "%r" for master "%r".' %
                             (buildername, mastername))

    self.bot_type = self.bot_config['bot_type']
    recipe_config_name = self.bot_config['recipe_config']
    self.recipe_config = recipe_configs.get(recipe_config_name)
    assert self.recipe_config, (
        'Cannot find recipe_config "%s" for builder "%r".' %
        (recipe_config_name, buildername))

    chromium_kwargs = self.bot_config.get('chromium_config_kwargs', {})
    if self.recipe_config.get('chromium_android_config'):
      self.m.chromium_android.set_config(
          self.recipe_config['chromium_android_config'], **chromium_kwargs)

    self.m.chromium.set_config(self.recipe_config['chromium_config'],
                               **chromium_kwargs)
    self.m.gclient.set_config(self.recipe_config['gclient_config'])

    # Support applying configs both at the bot and the recipe config level.
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    self.m.chromium.apply_config('gn')

    if self.m.tryserver.is_tryserver:
      if self.m.platform.is_win:
        # Windows builds are currently failing due to crbug.com/659439 when
        # fastbuild is enabled since it implies symbol_level=2. So we can only
        # enable dcheck for those.
        self.m.chromium.apply_config('dcheck')
      else:
        self.m.chromium.apply_config('trybot_flavor')

  @property
  def should_build(self):
    return self.bot_type in ('builder', 'builder_tester')

  @property
  def should_test(self):
    return self.bot_type in ('tester', 'builder_tester')

  @property
  def should_upload_build(self):
    return self.bot_config.get('triggers')

  @property
  def should_download_build(self):
    return self.bot_config.get('parent_buildername')

  def checkout(self):
    update_step = self.m.bot_update.ensure_checkout()
    assert update_step.json.output['did_run']
    self.revision = update_step.presentation.properties['got_revision']

  def maybe_trigger(self):
    triggers = self.bot_config.get('triggers')
    properties = {
      'revision': self.revision,
      'parent_got_revision': self.revision,
      'parent_buildername': self.m.properties.get('buildername'),
    }
    if triggers:
      if self.m.runtime.is_luci:
        self.m.scheduler.emit_trigger(
            self.m.scheduler.BuildbucketTrigger(properties=properties),
            project='libyuv', jobs=triggers)
      else:
        self.m.trigger(*[{
          'builder_name': builder_name,
          'properties': properties,
        } for builder_name in triggers])


  def package_build(self):
    upload_url = self.m.archive.legacy_upload_url(
        self.master_config.get('build_gs_bucket'),
        extra_url_components=self.m.properties['mastername'])
    self.m.archive.zip_and_upload_build(
        'package build',
        self.m.chromium.c.build_config_fs,
        upload_url,
        build_revision=self.revision)

  def extract_build(self):
    if not self.m.properties.get('parent_got_revision'):
      raise self.m.step.StepFailure(
         'Testers cannot be forced without providing revision information. '
         'Please select a previous build and click [Rebuild] or force a build '
         'for a Builder instead (will trigger new runs for the testers).')

    # Ensure old build directory isn't being used by removing it.
    self.m.file.rmtree(
        'build directory',
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

    download_url = self.m.archive.legacy_download_url(
       self.master_config.get('build_gs_bucket'),
       extra_url_components=self.m.properties['mastername'])
    self.m.archive.download_and_unzip_build(
        'extract build',
        self.m.chromium.c.build_config_fs,
        download_url,
        build_revision=self.revision)

  def runtests(self):
    """Add a suite of test steps."""
    with self.m.step.defer_results():
      if self.m.chromium.c.TARGET_PLATFORM == 'android':
        self.m.chromium_android.common_tests_setup_steps()
        self.m.chromium_android.run_test_suite('libyuv_unittest')
        self.m.chromium_android.shutdown_device_monitor()
        self.m.chromium_android.logcat_dump(
            gs_bucket=self.master_config.get('build_gs_bucket'))
        self.m.chromium_android.stack_tool_steps(force_latest_version=True)
        self.m.chromium_android.test_report()
      else:
        self.m.chromium.runtest('libyuv_unittest')
