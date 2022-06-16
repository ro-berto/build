# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_test_data(filename):
  """Return test data as str"""
  with open(os.path.join(THIS_DIR, filename), 'rb') as fp:
    return fp.read()
