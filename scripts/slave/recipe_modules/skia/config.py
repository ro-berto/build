# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Dict, Set, Single, Static
from recipe_engine.config_types import Path

# TODO(luqui): Separate this out so we can make the recipes independent of
# build/.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))))

from common.skia import builder_name_schema


CONFIG_COVERAGE = 'Coverage'
CONFIG_DEBUG = 'Debug'
CONFIG_RELEASE = 'Release'
VALID_CONFIGS = (CONFIG_COVERAGE, CONFIG_DEBUG, CONFIG_RELEASE)


def BaseConfig(BUILDER_NAME, MASTER_NAME, SLAVE_NAME, **_kwargs):
  equal_fn = lambda tup: ('%s=%s' % tup)
  return ConfigGroup(
    BUILDER_NAME = Static(str(BUILDER_NAME)),
    MASTER_NAME = Static(str(MASTER_NAME)),
    SLAVE_NAME = Static(str(SLAVE_NAME)),
    build_targets = Single(list),
    builder_cfg = Single(dict),
    configuration = Single(str),
    do_test_steps = Single(bool),
    do_perf_steps = Single(bool),
    extra_env_vars = Single(dict),
    gyp_env = ConfigGroup(
      GYP_DEFINES = Dict(equal_fn, ' '.join, (basestring,int,Path)),
    ),
    is_trybot = Single(bool),
    role = Single(str),
  )


def get_extra_env_vars(builder_dict):
  env = {}
  if builder_dict.get('compiler') == 'Clang':
    env['CC'] = '/usr/bin/clang'
    env['CXX'] = '/usr/bin/clang++'
  return env


def gyp_defs_from_builder_dict(builder_dict):
  gyp_defs = {}

  # skia_arch_type.
  if builder_dict['role'] == builder_name_schema.BUILDER_ROLE_BUILD:
    arch = builder_dict['target_arch']
  elif builder_dict['role'] == builder_name_schema.BUILDER_ROLE_HOUSEKEEPER:
    arch = None
  else:
    arch = builder_dict['arch']

  arch_types = {
    'x86':      'x86',
    'x86_64':   'x86_64',
    'Arm7':     'arm',
    'Arm64':    'arm64',
    'Mips':     'mips32',
    'Mips64':   'mips64',
    'MipsDSP2': 'mips32',
  }
  if arch in arch_types:
    gyp_defs['skia_arch_type']  = arch_types[arch]

  # housekeeper: build shared lib.
  if builder_dict['role'] == builder_name_schema.BUILDER_ROLE_HOUSEKEEPER:
    gyp_defs['skia_shared_lib'] = '1'

  # skia_gpu.
  if builder_dict.get('cpu_or_gpu') == 'CPU':
    gyp_defs['skia_gpu'] = '0'

  # skia_warnings_as_errors.
  werr = False
  if builder_dict['role'] == builder_name_schema.BUILDER_ROLE_BUILD:
    if 'Win' in builder_dict.get('os', ''):
      if not ('GDI' in builder_dict.get('extra_config', '') or
              'Exceptions' in builder_dict.get('extra_config', '')):
        werr = True
    elif ('Mac' in builder_dict.get('os', '') and
          'Android' in builder_dict.get('extra_config', '')):
      werr = False
    else:
      werr = True
  gyp_defs['skia_warnings_as_errors'] = str(int(werr))  # True/False -> '1'/'0'

  # Win debugger.
  if 'Win' in builder_dict.get('os', ''):
    gyp_defs['skia_win_debuggers_path'] = 'c:/DbgHelp'

  # Qt SDK (Win).
  if 'Win' in builder_dict.get('os', ''):
    if builder_dict.get('os') == 'Win8':
      gyp_defs['qt_sdk'] = 'C:/Qt/Qt5.1.0/5.1.0/msvc2012_64/'
    else:
      gyp_defs['qt_sdk'] = 'C:/Qt/4.8.5/'

  # ANGLE.
  if builder_dict.get('extra_config') == 'ANGLE':
    gyp_defs['skia_angle'] = '1'

  # GDI.
  if builder_dict.get('extra_config') == 'GDI':
    gyp_defs['skia_gdi'] = '1'

  # Build with Exceptions on Windows.
  if ('Win' in builder_dict.get('os', '') and
      builder_dict.get('extra_config') == 'Exceptions'):
    gyp_defs['skia_win_exceptions'] = '1'

  # iOS.
  if (builder_dict.get('os') == 'iOS' or
      builder_dict.get('extra_config') == 'iOS'):
    gyp_defs['skia_os'] = 'ios'

  # Shared library build.
  if builder_dict.get('extra_config') == 'Shared':
    gyp_defs['skia_shared_lib'] = '1'

  # PDF viewer in GM.
  if (builder_dict.get('os') == 'Mac10.8' and
      builder_dict.get('arch') == 'x86_64' and
      builder_dict.get('configuration') == 'Release'):
    gyp_defs['skia_run_pdfviewer_in_gm'] = '1'

  # Clang.
  if builder_dict.get('compiler') == 'Clang':
    gyp_defs['skia_clang_build'] = '1'

  # Valgrind.
  if 'Valgrind' in builder_dict.get('extra_config', ''):
    gyp_defs['skia_release_optimization_level'] = '1'

  # Link-time code generation just wastes time on compile-only bots.
  if (builder_dict.get('role') == builder_name_schema.BUILDER_ROLE_BUILD and
      builder_dict.get('compiler') == 'MSVC'):
    gyp_defs['skia_win_ltcg'] = '0'

  # Mesa.
  if (builder_dict.get('extra_config') == 'Mesa' or
      builder_dict.get('cpu_or_gpu_value') == 'Mesa'):
    gyp_defs['skia_mesa'] = '1'

  # SKNX_NO_SIMD
  if builder_dict.get('extra_config') == 'SKNX_NO_SIMD':
    gyp_defs['sknx_no_simd'] = '1'

  # skia_use_android_framework_defines.
  if builder_dict.get('extra_config') == 'Android_FrameworkDefs':
    gyp_defs['skia_use_android_framework_defines'] = '1'

  return gyp_defs


def build_targets_from_builder_dict(builder_dict):
  """Return a list of targets to build, depending on the builder type."""
  if builder_dict['role'] in ('Test', 'Perf') and builder_dict['os'] == 'iOS':
    return ['iOSShell']
  elif builder_dict['role'] == builder_name_schema.BUILDER_ROLE_TEST:
    return ['dm', 'nanobench']
  elif builder_dict['role'] == builder_name_schema.BUILDER_ROLE_PERF:
    return ['nanobench']
  else:
    return ['most']


config_ctx = config_item_context(BaseConfig)


@config_ctx(is_root=True)
def skia(c):
  """Base config for Skia."""
  c.builder_cfg = builder_name_schema.DictForBuilderName(c.BUILDER_NAME)
  c.build_targets = build_targets_from_builder_dict(c.builder_cfg)
  c.role = c.builder_cfg['role']
  if c.role == builder_name_schema.BUILDER_ROLE_HOUSEKEEPER:
    c.configuration = CONFIG_RELEASE
  else:
    c.configuration = c.builder_cfg.get('configuration', CONFIG_DEBUG)
  c.do_test_steps = c.role == builder_name_schema.BUILDER_ROLE_TEST
  c.do_perf_steps = (c.role == builder_name_schema.BUILDER_ROLE_PERF or
                     (c.role == builder_name_schema.BUILDER_ROLE_TEST and
                      c.configuration == CONFIG_DEBUG) or
                     'Valgrind' in c.BUILDER_NAME)
  c.gyp_env.GYP_DEFINES.update(gyp_defs_from_builder_dict(c.builder_cfg))
  c.is_trybot = builder_name_schema.IsTrybot(c.BUILDER_NAME)
  c.extra_env_vars = get_extra_env_vars(c.builder_cfg)
  arch = (c.builder_cfg.get('arch') or c.builder_cfg.get('target_arch'))
  if ('Win' in c.builder_cfg.get('os', '') and arch == 'x86_64'):
    c.configuration += '_x64'

