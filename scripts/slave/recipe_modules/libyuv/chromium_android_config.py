# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_android import CONFIG_CTX


@CONFIG_CTX(includes=['base_config'])
def libyuv(_):
  pass
