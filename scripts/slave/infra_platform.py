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
  plat, arch = sys.platform, platform.architecture()[0]

  if plat.startswith('linux'):
    plat = 'linux'
  elif plat.startswith(('win', 'cygwin')):
    plat = 'win'
  elif plat.startswith(('darwin', 'mac')):
    plat = 'mac'
  else:  # pragma: no cover
    raise ValueError("Don't understand platform [%s]" % (plat,))

  if arch == '64bit':
    bits = 64
  elif arch == '32bit':
    bits = 32
  else:  # pragma: no cover
    raise ValueError("Don't understand architecture [%s]" % (arch,))

  return plat, bits


def cascade_config(config):
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
      'baz': 'baz-linux-amd64',
    },
  }

  The resulting dictionary would be:
  {
    'foo': 'foo-generic',
    'bar': 'bar-linux',
    'baz': 'baz-linux-amd64',
  }

  Args:
    config (dict): Dictionary keyed on platform tuples.
  """
  # Cascade the platform configuration.
  p = get()
  result = {}
  for i in xrange(len(p)+1):
    result.update(config.get(p[:i], {}))
  return result
