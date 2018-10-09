# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['chromium_android'].CONFIG_CTX
from recipe_engine.config_types import Path


@CONFIG_CTX(includes=['base_config', 'use_devil_provision'])
def webrtc(_):
  pass
