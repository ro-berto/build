#!/usr/bin/env vpython

# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests that the tools/build annotated_run wrapper actually runs."""

import sys
import unittest

import mock

import test_env  # pylint: disable=relative-import

from slave import infra_platform


class TestGet(unittest.TestCase):

  @mock.patch('slave.infra_platform.sys')
  @mock.patch('platform.machine')
  @mock.patch('platform.architecture')
  def test_get(self, plat_arch, plat_machine, sys_platform):

    for plat, mach, arch, result in (
        ('linux1', 'armv7l', '32bit', ('linux', 'armv6l', 32)),
        ('linux1', 'arm64', '64bit', ('linux', 'arm64', 64)),
        ('linux1', 'aarch64', '64bit', ('linux', 'arm64', 64)),
        ('linux1', 'AMD64', '64bit', ('linux', 'x86_64', 64)),
        ('windows', 'i386', '32bit', ('win', 'x86', 32)),
        ('darwin', 'x86_64', '64bit', ('mac', 'x86_64', 64)),
    ):
      sys_platform.platform = plat
      plat_machine.return_value = mach
      plat_arch.return_value = (arch, 'ELF')
      self.assertEqual(infra_platform.get(), result)


class TestCascadeConfig(unittest.TestCase):

  def test_cascade_config(self):
    v = infra_platform.cascade_config({
      (): {
        'generic': True,
      },
      ('linux',): {
        'os': 'linux',
      },
      ('linux', 32): {
        'bits': 'linux-32',
      },
      ('linux', 'armv6l'): {
        'machine': 'linux-armv6l',
      },
      ('linux', 'x86'): {
        'machine': 'linux-x86',
      },
      ('linux', 'armv6l', 32): {
        'all': 'linux-armv6l-32',
      },
    }, plat=('linux', 'armv6l', 32))
    self.assertEqual(v, {
        'generic': True,
        'os': 'linux',
        'bits': 'linux-32',
        'machine': 'linux-armv6l',
        'all': 'linux-armv6l-32',
    })


if __name__ == '__main__':
  unittest.main()
