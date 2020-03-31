# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def CreateBuilderConfig(os, bits, angle_tot, swiftshader_tot):
  configs = []
  if angle_tot:
    configs.append('angle_top_of_tree')
  if swiftshader_tot:
    configs.append('swiftshader_top_of_tree')
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-swangle-archive',
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
          'mb_luci_auth',
      ],
      gclient_config='chromium',
      gclient_apply_config=configs,
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': bits,
      },
      bot_type=bot_spec.BUILDER_TESTER,
      testing={
          'platform': os,
      },
      serialize_tests=True,
  )


SPEC = {
    'builders': {
        'linux-swangle-tot-angle-x64':
            CreateBuilderConfig(
                'linux', 64, angle_tot=True, swiftshader_tot=False),
        'linux-swangle-tot-angle-x86':
            CreateBuilderConfig(
                'linux', 32, angle_tot=True, swiftshader_tot=False),
        'linux-swangle-tot-swiftshader-x64':
            CreateBuilderConfig(
                'linux', 64, angle_tot=False, swiftshader_tot=True),
        'linux-swangle-tot-swiftshader-x86':
            CreateBuilderConfig(
                'linux', 32, angle_tot=False, swiftshader_tot=True),
        'linux-swangle-x64':
            CreateBuilderConfig(
                'linux', 64, angle_tot=False, swiftshader_tot=False),
        'linux-swangle-x86':
            CreateBuilderConfig(
                'linux', 32, angle_tot=False, swiftshader_tot=False),
        'win-swangle-tot-angle-x64':
            CreateBuilderConfig(
                'win', 64, angle_tot=True, swiftshader_tot=False),
        'win-swangle-tot-angle-x86':
            CreateBuilderConfig(
                'win', 32, angle_tot=True, swiftshader_tot=False),
        'win-swangle-tot-swiftshader-x64':
            CreateBuilderConfig(
                'win', 64, angle_tot=False, swiftshader_tot=True),
        'win-swangle-tot-swiftshader-x86':
            CreateBuilderConfig(
                'win', 32, angle_tot=False, swiftshader_tot=True),
        'win-swangle-x64':
            CreateBuilderConfig(
                'win', 64, angle_tot=False, swiftshader_tot=False),
        'win-swangle-x86':
            CreateBuilderConfig(
                'win', 32, angle_tot=False, swiftshader_tot=False),
    },
}
