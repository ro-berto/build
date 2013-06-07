# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test inputs for recipes/blink_trybot.py"""

SUCCESS_DATA = {}

FAIL_DATA = {
  'webkit_tests (with patch)': (1, {'crazy': ['data', 'format']}),
  'webkit_tests (without patch)': (1, {'crazy': ['data', 'format']})
}

for result in ['success', 'fail']:
  for build_config in ['Release', 'Debug']:
    def closure(result_, build_config_):
      return lambda api: {
        'build_properties': api.tryserver_build_properties(
          build_config=build_config_,
          config_name='blink',
        ),
        'test_data': globals()['%s_DATA' % result_.upper()]
      }
    ret = closure(result, build_config)
    globals()['%s_%s_test' % (result, build_config.lower())] = ret

