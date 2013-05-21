# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test inputs for recipes/toolkit.py"""

def basic_test(api):
  return {
    'build_properties': api.tryserver_build_properties(
      repository="https://github.com/toolkitchen/toolkit"
    ),
    'test_data': {
      'gen step(gen_steps.py)': (0, [
        {'name': 'bogus', 'cmd': ['bogus.py', '--arg']}
      ])
    }
  }
