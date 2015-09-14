# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

GPU_ISOLATES = (
  'angle_unittests',
  'content_gl_tests',
  'gl_tests',
  'gles2_conform_test',
  'gpu_unittests',
  'tab_capture_end2end_tests',
  'telemetry_gpu_test',
)

# Until the media-only tests are extracted from content_unittests and
# these both can be run on the commit queue with
# --require-audio-hardware-for-testing, run them only on the FYI
# waterfall.
FYI_ONLY_GPU_ISOLATES = (
  'audio_unittests',
  'content_unittests',
)

# This will be folded into the list above once ANGLE is running on all
# platforms.
WIN_AND_LINUX_ONLY_FYI_ONLY_GPU_ISOLATES = (
  'angle_end2end_tests',
  'angle_deqp_gles2_tests',
)

WIN_ONLY_FYI_ONLY_GPU_ISOLATES = (
  'angle_deqp_gles3_tests',
)

# A list of all the Linux FYI isolates for testing
ALL_LINUX_FYI_GPU_ISOLATES = (
  GPU_ISOLATES +
  FYI_ONLY_GPU_ISOLATES +
  WIN_AND_LINUX_ONLY_FYI_ONLY_GPU_ISOLATES
)

# A list of all Windows FYI isolates for testing
ALL_WIN_FYI_GPU_ISOLATES = (
  GPU_ISOLATES +
  FYI_ONLY_GPU_ISOLATES +
  WIN_AND_LINUX_ONLY_FYI_ONLY_GPU_ISOLATES +
  WIN_ONLY_FYI_ONLY_GPU_ISOLATES
)

# A list of all ANGLE trybot isolates for testing
ALL_ANGLE_TRYBOT_GPU_ISOLATES = (
  GPU_ISOLATES +
  FYI_ONLY_GPU_ISOLATES +
  WIN_AND_LINUX_ONLY_FYI_ONLY_GPU_ISOLATES
)
