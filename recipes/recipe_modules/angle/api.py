# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb


class ANGLEApi(recipe_api.RecipeApi):

  def __init__(self, properties, **kwargs):
    super(ANGLEApi, self).__init__(**kwargs)

  def _apply_bot_config(self, platform, toolchain):
    self.set_config('angle', optional=True)
    if toolchain == 'clang':
      self.m.chromium.set_config('angle_clang')
    else:
      self.m.chromium.set_config('angle_non_clang')
    if platform == 'android':
      self.m.gclient.set_config('angle_android')
    else:
      self.m.gclient.set_config('angle')

  def _checkout(self):
    # Checkout angle and its dependencies (specified in DEPS) using gclient.
    solution_path = self.m.path['cache'].join('builder')
    self.m.file.ensure_directory('init cache if not exists', solution_path)
    with self.m.context(cwd=solution_path):
      update_step = self.m.bot_update.ensure_checkout()
      self.m.chromium.runhooks()
      return update_step

  def _compile(self, toolchain):
    builder_id = self.m.chromium.get_builder_id()
    raw_result = self.m.chromium_tests.run_mb_and_compile(['all'],
                                                          None,
                                                          '',
                                                          builder_id=builder_id)
    if self.m.platform.is_win and toolchain == 'msvc':
      self.m.chromium.taskkill()
    return raw_result

  def _trace_tests(self):
    self.m.goma.ensure_goma()
    checkout = self.m.path['checkout']
    with self.m.context(cwd=checkout):
      cmd = [
          'python3',
          'src/tests/capture_replay_tests.py',
          '--use-goma',
          '--goma-dir=%s' % self.m.goma.goma_dir,
          '--log',
          'debug',
          '--gtest_filter=*/ES2_Vulkan_SwiftShader',
          '--out-dir=%s' % checkout.join('out', 'CaptureReplayTest'),
          '--depot-tools-path=%s' % self.m.depot_tools.root,
      ]

      if self.m.platform.is_linux:
        cmd += ['--xvfb']

      # TODO(jmadill): Figure out why Linux is failing. http://anglebug.com/5530
      if not self.m.platform.is_linux:
        self.m.goma.start()
        self.m.step('Run trace tests', cmd)
        self.m.goma.stop(0)

  def steps(self):
    toolchain = self.m.properties.get('toolchain', 'clang')
    platform = self.m.properties.get('platform', self.m.platform.name)
    test_mode = self.m.properties.get('test_mode')
    self._apply_bot_config(platform, toolchain)
    self._checkout()
    if test_mode == 'checkout_only':
      pass
    elif test_mode == 'trace_tests':
      self._trace_tests()
    else:
      raw_result = self._compile(toolchain)
      if raw_result.status != common_pb.SUCCESS:
        return raw_result
      # TODO(jmadill): Swarming tests. http://anglebug.com/5114
