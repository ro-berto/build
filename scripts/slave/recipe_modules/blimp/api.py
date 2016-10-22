# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

from recipe_engine import recipe_api
from recipe_engine.config_types import Path

class BlimpApi(recipe_api.RecipeApi):
  def get_config_defaults(self):
    return {
        'CHECKOUT_PATH': self.m.path['checkout'],
    }

  def _start_engine_forwarder(self, output_linux_dir, **kwargs):
    args = [
        '-l', output_linux_dir,
        'run',
    ]
    self.m.python('[Blimp] Starting engine and forwarder',
                  self.c.client_engine_integration_script,
                  args,
                  **kwargs)

  def _stop_engine_forwarder(self, output_linux_dir, **kwargs):
    args = [
        '-l', output_linux_dir,
        'stop',
    ]
    self.m.python('[Blimp] Killing engine and forwarder',
                  self.c.client_engine_integration_script,
                  args,
                  **kwargs)


  def load_client(self, output_linux_dir, apk_path, **kwargs):
    """Installs apk in client and runs blimp."""
    args = [
        '-l', output_linux_dir,
        'load',
        '--apk-path', apk_path,
    ]
    self.m.python('[Blimp] Installing apk and running blimp',
                  self.c.client_engine_integration_script,
                  args,
                  **kwargs)

  @contextlib.contextmanager
  def engine_forwarder(self, output_linux_dir, **kwargs):
    try:
      self._start_engine_forwarder(output_linux_dir, **kwargs)
      yield
    finally:
      self._stop_engine_forwarder(output_linux_dir)

