# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import BadConf
from recipe_engine.config_types import Path

import DEPS
CONFIG_CTX = DEPS['chromium'].CONFIG_CTX


@CONFIG_CTX(includes=['ninja', 'default_compiler', 'goma'])
def webrtc_default(c):
  c.compile_py.default_targets = []


# TODO(kjellander): Remove as soon there's a way to get the sanitizer bots to
# set swarming tags properly without the chromium recipe module configs (which
# depend on clang)
@CONFIG_CTX(includes=['ninja', 'clang', 'goma'])
def webrtc_clang(c):
  c.compile_py.default_targets = []
