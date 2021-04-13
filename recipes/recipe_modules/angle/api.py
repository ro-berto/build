# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class ANGLEApi(recipe_api.RecipeApi):

  def __init__(self, **kwargs):
    super(ANGLEApi, self).__init__(**kwargs)

  def apply_bot_config(self, clang):
    self.set_config('angle', optional=True)
    if clang:
      self.m.chromium.set_config('angle_clang')
    else:
      self.m.chromium.set_config('angle_non_clang')
    # TODO(jmadill): Rename after depot tools update. http://anglebug.com/5114
    self.m.gclient.set_config('angle_2')

  def is_gcc(self, clang):
    return not clang and self.m.platform.is_linux

  def checkout(self):
    # Checkout angle and its dependencies (specified in DEPS) using gclient.
    solution_path = self.m.path['cache'].join('builder')
    self.m.file.ensure_directory('init cache if not exists', solution_path)
    with self.m.context(cwd=solution_path):
      update_step = self.m.bot_update.ensure_checkout()
      self.m.chromium.runhooks()
      return update_step

  def compile(self, clang):
    self.checkout()
    # Don't compile with gcc
    if self.is_gcc(clang):
      return
    builder_id = self.m.chromium.get_builder_id()
    self.m.chromium_tests.run_mb_and_compile(['all'],
                                             None,
                                             '',
                                             builder_id=builder_id)

  def trace_tests(self, api):
    self.checkout()
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
