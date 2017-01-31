#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module to resolve the current platform and bitness that works across
infrastructure systems.
"""


import itertools
import platform
import sys


def get():
  """Returns the normalized platform and bitness values.

  Platform: linux, mac, win
  Machine:
    - x86_64 (Intel 64-bit)
    - x86 (Intel 32-bit)
    - armv6l (ARM 32-bit v6)
    - arm64 (ARM 64-bit)
    - <other> (Unknown, returned by platform.machine())
  Bits: 32, 64

  Returns:
    plat (str): The name of the current platform.
    machine (str): The normalized machine type.
    bits (int): The bitness of the current platform, one of 32, 64.

  Raises:
    ValueError if both the platform and bitness could not be resolved.
  """
  plat = sys.platform
  machine = platform.machine()
  arch = platform.architecture()[0]

  if plat.startswith('linux'):
    plat = 'linux'
  elif plat.startswith(('win', 'cygwin')):
    plat = 'win'
  elif plat.startswith(('darwin', 'mac')):
    plat = 'mac'
  else:  # pragma: no cover
    raise ValueError("Don't understand platform [%s]" % (plat,))

  # Normalize "machine".
  if machine.startswith('arm'):
    if machine.startswith('arm64'):
      machine = 'arm64'
    elif machine.endswith('l'):
      # 32-bit ARM: Standardize on ARM v6 baseline.
      machine = 'armv6l'
  elif machine in ('amd64',):
    machine = 'x86_64'
  elif machine in ('i386', 'i686'):
    machine = 'x86'

  # Extract architecture.
  if arch == '64bit':
    bits = 64
  elif arch == '32bit':
    bits = 32
  else:  # pragma: no cover
    raise ValueError("Don't understand architecture [%s]" % (arch,))

  return plat, machine, bits


def cascade_config(config, plat=None):
  """Returns (dict): The constructed configuration dictionary.

  Traverses the supplied configuration dictionary, building a cascading
  configuration by folding in values of increasingly-specialized platform tuple
  keys. The platform tuple that is traversed is the one returned by 'get'.

  For example, on a 64-bit Linux platform with a 'config' dictionary of:
  config = {
    (): {
      'foo': 'foo-generic',
      'bar': 'bar-generic',
      'baz': 'baz-generic',
    },
    ('linux',): {
      'bar': 'bar-linux',
      'baz': 'baz-linux',
    },
    ('linux', 64): {
      'qux': 'qux-linux-64bit-generic',
    },
    ('linux', 'x86_64'): {
      'baz': 'baz-linux-amd64',
    },
  }

  The resulting dictionary would be:
  {
    'foo': 'foo-generic',
    'bar': 'bar-linux',
    'baz': 'baz-linux-amd64',
    'qux': 'qux-linux-64bit-generic',
  }

  Args:
    config (dict): Dictionary keyed on platform tuples.
  """
  # Cascade the platform configuration.
  plat = plat or get()
  result = {}
  for r in xrange(len(plat)+1):
    for c in itertools.combinations(plat, r):
      result.update(config.get(c, {}))
  return result
