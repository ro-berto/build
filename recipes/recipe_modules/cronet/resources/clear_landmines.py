#!/usr/bin/env python3
# Copyright (c) 2022 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import subprocess
import sys

proc = subprocess.Popen(
    sys.argv[1], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
out, err = proc.communicate()
with open(sys.argv[2], 'w') as f:
  f.writelines(out)