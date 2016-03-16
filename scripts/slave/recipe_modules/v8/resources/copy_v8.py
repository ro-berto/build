#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Copy a directory and ignore some absolute paths."""

import os.path
import shutil
import sys

def ignore(p, files):
  return [
    f for path in sys.argv[3:]
      for f in files
        if os.path.abspath(os.path.join(p, f)) == path]

shutil.copytree(
    sys.argv[1],
    sys.argv[2],
    ignore=ignore,
)