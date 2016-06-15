#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script that makes an mb config use gn where it's supposed to use gyp.

This is used to run gn on all gyp bots as an fyi step.
"""

import sys

with open(sys.argv[1]) as f:
  with open(sys.argv[2], 'w') as g:
    g.write(f.read().replace("'type': 'gyp'", "'type': 'gn'"))