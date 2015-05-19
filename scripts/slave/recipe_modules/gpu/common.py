# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

GPU_ISOLATES = (
  'angle_unittests',
  'content_gl_tests',
  'content_unittests',
  'gl_tests',
  'gles2_conform_test',
  'gpu_unittests',
  'media_unittests',
  'tab_capture_end2end_tests',
  'telemetry_gpu_test',
)

# This will be folded into the list above once ANGLE is running on all
# platforms.
WIN_ONLY_GPU_ISOLATES = (
  'angle_end2end_tests',
)
