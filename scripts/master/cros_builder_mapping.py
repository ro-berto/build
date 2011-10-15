# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This is a dictionary that maps waterfall dashboard names to cbuildbot_configs.
# In order to add a new dict, you must edit this first.
NAME_CONFIG_DICT = {
  'x86 generic PFQ': 'x86-generic-pre-flight-queue',
  'x86 generic commit queue': 'x86-generic-commit-queue',
  'arm generic PFQ': 'arm-generic-bin',
  'tegra2 PFQ': 'arm-tegra2-bin',
  'x86 generic full': 'x86-generic-full',
  'arm generic full': 'arm-generic-full',
  'tegra2 full': 'arm-tegra2-full',
  'tegra2 seaboard full': 'arm-tegra2-seaboard-full',
  'x86 pineview full': 'x86-pineview-full',
  'x86 generic chrome PFQ': 'x86-generic-chrome-pre-flight-queue',
  'arm generic chrome PFQ': 'arm-generic-chrome-pre-flight-queue',
  'tegra2 chrome PFQ': 'arm-tegra2-chrome-pre-flight-queue',
  'chromiumos sdk': 'chromiumos-sdk',
  'refresh packages': 'refresh-packages',
  'x86 generic ASAN': 'x86-generic-asan',
}

# CONFIG_NAME_DICT is an inversion of NAME_CONFIG_DICT
CONFIG_NAME_DICT = dict([[v, k] for k, v in NAME_CONFIG_DICT.items()])
