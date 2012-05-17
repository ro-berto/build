# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromeos_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

defaults['category'] = '2chromiumos'

# TODO(petermayo) Make this sensitive to LKGM changes too, crosbug.com/20798

S(name='chromium_cros', branch='src', treeStableTimer=60)


B('ChromiumOS (x86)',
  factory='x86',
  gatekeeper='closer|watch',
  builddir='chromium-tot-chromeos-x86-generic',
  scheduler='chromium_cros',
  auto_reboot=True,
  notify_on_missing=True)
F('x86', chromeos_factory.CbuildbotFactory(
  buildroot='/b/cbuild.x86',
  crostools_repo=None,
  pass_revision=True,
  params='x86-generic-tot-chrome-pfq-informational').get_factory())


B('ChromiumOS (amd64)',
  factory='amd64',
  gatekeeper='watch',
  #gatekeeper='closer|watch',
  builddir='chromium-tot-chromeos-amd64',
  scheduler='chromium_cros',
  auto_reboot=True,
  notify_on_missing=True)
F('amd64', chromeos_factory.CbuildbotFactory(
  buildroot='/b/cbuild.amd64',
  crostools_repo=None,
  pass_revision=True,
  params='amd64-generic-tot-chrome-pfq-informational').get_factory())


B('ChromiumOS (arm)',
  factory='arm',
  gatekeeper='closer|watch',
  builddir='chromium-tot-chromeos-arm',
  scheduler='chromium_cros',
  auto_reboot=True,
  notify_on_missing=True)
F('arm', chromeos_factory.CbuildbotFactory(
  buildroot='/b/cbuild.arm',
  crostools_repo=None,
  pass_revision=True,
  params='arm-generic-tot-chrome-pfq-informational').get_factory())


B('ChromiumOS (tegra2)',
  factory='tegra2',
  gatekeeper='closer|watch',
  builddir='chromium-tot-chromeos-tegra2',
  scheduler='chromium_cros',
  auto_reboot=True,
  notify_on_missing=True)
F('tegra2', chromeos_factory.CbuildbotFactory(
  buildroot='/b/cbuild.tegra2',
  crostools_repo=None,
  pass_revision=True,
  params='arm-tegra2-tot-chrome-pfq-informational').get_factory())


B('ChromiumOS (daisy)',
  factory='daisy',
  gatekeeper='closer|watch',
  builddir='chromium-tot-chromeos-daisy',
  scheduler='chromium_cros',
  auto_reboot=True,
  notify_on_missing=True)
F('daisy', chromeos_factory.CbuildbotFactory(
  buildroot='/b/cbuild.daisy',
  crostools_repo=None,
  pass_revision=True,
  params='daisy-tot-chrome-pfq-informational').get_factory())


def Update(config, active_master, c):
  return helper.Update(c)
