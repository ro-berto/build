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
  build_path = [
      # This will allow scripts to import 'recipes'. You shouldn't add a
      # dependency on this.
      cwd,
      os.path.join(cwd, 'scripts'),
      os.path.join(cwd, 'recipes'),
      os.path.join(cwd, 'site_config'),
  ]
  return pythonpath.Append(*build_path)
