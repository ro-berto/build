# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Extension script to <build>/scripts/common/env.py to add 'build_internal'
paths.
"""

import os

def Extend(pythonpath, cwd):
  """Path extension function (see common.env).

  In this invocation, 'cwd' is the <build> directory.
  """
  third_party_base = os.path.join(cwd, 'third_party')
  build_path = [
      os.path.join(cwd, 'scripts'),
      os.path.join(cwd, 'site_config'),
      third_party_base,
  ]

  # Add 'BUILD/third_party' paths.
  build_path += [os.path.join(third_party_base, path) for path in (
      'buildbot_8_4p1',
      'buildbot_slave_8_4',
      'coverage-3.7.1',
      'decorator_3_3_1',
      'google_api_python_client',
      'httplib2/python2',
      'infra_libs',
      'jinja2',
      'markupsafe',
      'mock-1.0.1',
      'oauth2client',
      'pyasn1',
      'pyasn1-modules',
      'python-rsa',
      'requests_2_10_0',
      'setuptools-0.6c11',
      'sqlalchemy_0_7_1',
      'sqlalchemy_migrate_0_7_1',
      'tempita_0_5',
      'twisted_10_2',
      'uritemplate',

      'site-packages',
  )]
  return pythonpath.Append(*build_path)
