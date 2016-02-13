#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module to resolve the current platform and bitness that works across
infrastructure systems.
"""


import platform
import sys


def get():
  """Returns the normalized platform and bitness values.

  Returns:
    plat (str): The name of the current platform, one of "linux", "win", or
        "mac".
    bits (int): The bitness of the current platform, one of 32, 64.

  Raises:
    ValueError if both the platform and bitness could not be resolved.
  """
  plat, machine = sys.platform, platform.machine()

  if plat.startswith('linux'):
    plat = 'linux'
  elif plat.startswith(('win', 'cygwin')):
    plat = 'win'
  elif plat.startswith(('darwin', 'mac')):
    plat = 'mac'
  else:  # pragma: no cover
    raise ValueError("Don't understand platform [%s]" % (plat,))

  if machine == 'x86_64':
    bits = 64
  elif machine == 'i386':
    bits = 32
  else:  # pragma: no cover
    raise ValueError("Don't understand machine [%s]" % (machine,))

  return plat, bits
