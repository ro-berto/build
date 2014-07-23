# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Dict, Set, Single, Static
from slave.recipe_config_types import Path

from common.skia import builder_name_schema
from . import base_flavor


CONFIG_DEBUG = 'Debug'
CONFIG_RELEASE = 'Release'
VALID_CONFIGS = (CONFIG_DEBUG, CONFIG_RELEASE)


def BaseConfig(BUILDER_NAME, **_kwargs):
  equal_fn = lambda tup: ('%s=%s' % tup)
  return ConfigGroup(
    BUILDER_NAME = Static(BUILDER_NAME),
    build_targets = Single(list),
    builder_cfg = Single(dict),
    configuration = Single(str),
    do_test_steps = Single(bool),
    do_perf_steps = Single(bool),
    gyp_env = ConfigGroup(
      GYP_DEFINES = Dict(equal_fn, ' '.join, (basestring,int,Path)),
    ),
    role = Single(str),
  )


VAR_TEST_MAP = {
  'BUILDER_NAME': ('Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug',
                   'Build-Ubuntu13.10-GCC4.8-x86_64-Debug'),
}


def gyp_defs_from_builder_dict(builder_dict):
  gyp_defs = {}

  # skia_arch_width
  if builder_dict['role'] == builder_name_schema.BUILDER_ROLE_BUILD:
    arch = builder_dict['target_arch']
  else:
    arch = builder_dict['arch']
  skia_arch_width = {
    'x86': '32',
    'x86_64': '64',
    'Arm7': '32',
    'Arm64': '64',
    'Mips': '32',
    'Mips64': '64',
    'MipsDSP2': '32',
    'NaCl': None,
  }.get(arch)
  if skia_arch_width:
    gyp_defs['skia_arch_width'] = skia_arch_width

  # skia_gpu
  if builder_dict.get('gpu') == 'NoGPU':
    gyp_defs['skia_gpu'] = '0'

  # skia_warnings_as_errors
  if builder_dict['role'] == builder_name_schema.BUILDER_ROLE_BUILD:
    gyp_defs['skia_warnings_as_errors'] = '1'
  else:
    gyp_defs['skia_warnings_as_errors'] = '0'

  return gyp_defs


config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, '%(BUILDER_NAME)s')


@config_ctx(is_root=True)
def skia(c):
  """Base config for Skia."""
  # TODO(borenet): Build targets should change based on OS and various configs.
  c.build_targets = ['most']
  c.builder_cfg = builder_name_schema.DictForBuilderName(c.BUILDER_NAME)
  c.configuration = c.builder_cfg.get('configuration', CONFIG_DEBUG)
  c.role = c.builder_cfg['role']
  c.do_test_steps = c.role == builder_name_schema.BUILDER_ROLE_TEST
  c.do_perf_steps = (c.role == builder_name_schema.BUILDER_ROLE_PERF or
                     (c.role == builder_name_schema.BUILDER_ROLE_TEST and
                      c.configuration == CONFIG_DEBUG))
  c.gyp_env.GYP_DEFINES.update(gyp_defs_from_builder_dict(c.builder_cfg))

