#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Entry point for the dartium buildbots.

This script is called from buildbot and reports results using the buildbot
annotation scheme.
"""

import optparse
import sys

from common import chromium_utils


def main():
  parser = optparse.OptionParser()
  chromium_utils.AddPropertiesOptions(parser)
  options, _ = parser.parse_args()
  master_name = options.build_properties.get('mastername')

  if master_name == 'client.dart':
    return chromium_utils.RunCommand(
        [sys.executable,
         'src/build/buildbot_annotated_steps.py',
        ])
  else:
    raise RuntimeError('Unrecognized master: ' + master_name)


if __name__ == '__main__':
  sys.exit(main())
