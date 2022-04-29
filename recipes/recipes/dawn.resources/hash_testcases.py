#!/usr/bin/env python3
# Copyright (c) 2022 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import os
from shutil import copyfile
import sys

for arg in sys.argv[2:]:
  h = hashlib.md5(open(arg, "rb").read()).hexdigest()
  copyfile(arg, os.path.join(sys.argv[1], "trace_" + h))