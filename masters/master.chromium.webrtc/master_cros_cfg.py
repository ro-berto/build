# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromeos_factory
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler


def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


def CreateCbuildbotFactory(target, short_name):
  """Generate and register a ChromeOS builder along with its slave(s)."""

  # Factory with the steps to pull out a Chromium source tree (no compilation).
  # It uses an unused slave_type string to avoid adding the normal compile step.
  chrome_factory = linux().ChromiumWebRTCLatestFactory(slave_type='WebRtcCros')

  # Extend that factory with Cbuildbot build steps to build and test CrOS using
  # the Chrome from the above Chromium source tree.
  return chromeos_factory.CbuildbotFactory(
      params=target,
      buildroot='/b/cbuild.%s' % short_name,
      dry_run=True,
      chrome_root='.',  # Where ChromiumWebRTCLatestFactory has put "Chrome".
      factory=chrome_factory,
      slave_manager=False).get_factory()


S(name='chromium_cros', branch='trunk', treeStableTimer=0)

defaults['category'] = 'chromiumos'

B('ChromiumOS [x86]',
  factory='chromeos_x86_factory',
  builddir='chromium-webrtc-tot-chromeos-x86-generic',
  scheduler='chromium_cros',
  notify_on_missing=True)
F('chromeos_x86_factory',
  CreateCbuildbotFactory(target='x86-webrtc-chrome-pfq-informational',
                         short_name='x86'))

B('ChromiumOS [amd64]',
  factory='chromeos_amd64_factory',
  builddir='chromium-webrtc-tot-chromeos-amd64',
  scheduler='chromium_cros',
  notify_on_missing=True)
F('chromeos_amd64_factory',
  CreateCbuildbotFactory(target='amd64-webrtc-chrome-pfq-informational',
                         short_name='amd64'))

B('ChromiumOS [daisy]',
  factory='chromeos_daisy_factory',
  builddir='chromium-webrtc-tot-chromeos-daisy',
  scheduler='chromium_cros',
  notify_on_missing=True)
F('chromeos_daisy_factory',
  CreateCbuildbotFactory(target='daisy-webrtc-chrome-pfq-informational',
                         short_name='daisy'))


def Update(config, active_master, c):
  return helper.Update(c)
