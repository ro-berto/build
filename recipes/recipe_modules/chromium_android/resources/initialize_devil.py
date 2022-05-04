#!/usr/bin/env python3
# Copyright (c) 2022 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys
sys.path.append(sys.argv[1])
from devil import devil_env

devil_env.config.Initialize()
devil_env.config.PrefetchPaths(dependencies=['adb'])
