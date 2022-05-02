#!/usr/bin/env python3
# Copyright (c) 2022 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import subprocess
import sys

adb_path = sys.argv[1]
for device in sys.argv[2:]:
  print('Attempting to root device %s ...' % device)
  subprocess.check_call([adb_path, '-s', device, 'root'])
  subprocess.check_call([adb_path, '-s', device, 'wait-for-device'])
  print('Finished rooting device %s' % device)
