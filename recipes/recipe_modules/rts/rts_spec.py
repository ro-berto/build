# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.attr_utils import attrib, attrs


@attrs()
class RTSSpec(object):
  # The version of rts-chromium to pull from CIPD
  rts_chromium_version = attrib(str, default='latest')
  # The version of the RTS model to pull from CIPD
  model_version = attrib(str, default='latest')
  # The path to put RTS output, should match the value set in the GN args for
  # the builder
  skip_test_files_path = attrib(str)
  # The target change recall, or safety, must lie from (0, 1)
  target_change_recall = attrib(float, default=.99)
