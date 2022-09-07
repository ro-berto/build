# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_dawn_spec(os, bits, **kwargs):
  is_tester = kwargs.get('execution_mode') == builder_spec.TEST
  return builder_spec.BuilderSpec.create(
      chromium_config='chromium',
      chromium_apply_config=['mb'],
      gclient_config='chromium',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': bits,
          'TARGET_PLATFORM': os,
      },
      # The testers are running on linux thin bots regardless the os.
      simulation_platform='linux' if is_tester else os,
      build_gs_bucket='chromium-dawn-archive',
      **kwargs)

def CreateBuilderConfig(os, bits, top_of_tree):
  gclient_apply_config = ['dawn_top_of_tree'] if top_of_tree else []
  return _chromium_dawn_spec(
      os,
      bits,
      gclient_apply_config=gclient_apply_config,
      serialize_tests=True,
  )


def CreateTesterConfig(os, bits, builder):
  return _chromium_dawn_spec(
      os,
      bits,
      execution_mode=builder_spec.TEST,
      parent_buildername=builder,
      serialize_tests=True,
  )


# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.dawn.star
# * Dawn Linux x64 DEPS Builder
# * Dawn Linux x64 DEPS Release (Intel HD 630)
# * Dawn Linux x64 DEPS Release (NVIDIA)
# * Dawn Mac x64 DEPS Builder
# * Dawn Mac x64 DEPS Release (AMD)
# * Dawn Mac x64 DEPS Release (Intel)
# * Dawn Win10 x64 DEPS Builder
# * Dawn Win10 x64 DEPS Release (Intel HD 630)
# * Dawn Win10 x64 DEPS Release (NVIDIA)
# * Dawn Win10 x86 DEPS Builder
# * Dawn Win10 x86 DEPS Release (Intel HD 630)
# * Dawn Win10 x86 DEPS Release (NVIDIA)
# * Dawn Linux x64 Builder
# * Dawn Linux x64 Release (Intel HD 630)
# * Dawn Linux x64 Release (NVIDIA)
# * Dawn Win10 x64 Builder
# * Dawn Win10 x64 Release (Intel HD 630)
# * Dawn Win10 x64 Release (NVIDIA)
# * Dawn Win10 x86 Builder
# * Dawn Win10 x86 Release (Intel HD 630)
# * Dawn Win10 x86 Release (NVIDIA)
# * Dawn Win10 x64 ASAN Release

SPEC = {
    'Dawn Mac x64 Builder':
        CreateBuilderConfig('mac', 64, top_of_tree=True),
    # The Dawn Mac testers are actually running on thin Linux VMs.
    'Dawn Mac x64 Release (AMD)':
        CreateTesterConfig('mac', 64, 'Dawn Mac x64 Builder'),
    'Dawn Mac x64 Experimental Release (AMD)':
        CreateTesterConfig('mac', 64, 'Dawn Mac x64 Builder'),
    'Dawn Mac x64 Experimental Release (Intel)':
        CreateTesterConfig('mac', 64, 'Dawn Mac x64 Builder'),
    'Dawn Mac x64 Release (Intel)':
        CreateTesterConfig('mac', 64, 'Dawn Mac x64 Builder'),
}
