# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_configs_util import config_item_context, ConfigGroup
from slave.recipe_configs_util import DictConfig, StaticConfig
from slave.recipe_configs_util import BadConf

# Because of the way that we use decorators, pylint can't figure out the proper
# type signature of functions annotated with the @config_ctx decorator.
# pylint: disable=E1123

def norm_host_platform(plat):
  if plat.startswith('linux'):
    return 'linux'
  elif plat.startswith(('win', 'cygwin')):
    return 'win'
  elif plat.startswith(('darwin', 'mac')):
    return 'mac'
  else:  # pragma: no cover
    raise ValueError('Don\'t understand platform "%s"' % plat)

def norm_bits(arch):
  if not arch:
    return None
  return 64 if '64' in str(arch) else 32

def norm_arch(arch):
  if not arch:
    return None
  elif arch in ('x86_64', 'i386', 'intel'):
    return 'intel'
  elif arch == 'arm':
    return 'arm'
  elif arch == 'mips':
    return 'mips'
  else:  # pragma: no cover
    raise ValueError('Don\'t understand architecture "%s"' % arch)

def norm_build_config(build_config=None):
  return 'Release' if build_config == 'Release' else 'Debug'

# Schema for config items in this module.
def BaseConfig(HOST_PLATFORM=None, HOST_ARCH=None, HOST_BITS=None,
               TARGET_ARCH=None, TARGET_BITS=32,
               BUILD_CONFIG=norm_build_config(), **_kwargs):
  var_fun = lambda i: ('%s=%s' % i)
  return ConfigGroup(
    gyp_env = ConfigGroup(
      GYP_DEFINES = DictConfig(var_fun, ' '.join, (basestring,int)),
    ),

    BUILD_CONFIG = StaticConfig(norm_build_config(BUILD_CONFIG)),

    HOST_PLATFORM = StaticConfig(norm_host_platform(HOST_PLATFORM)),
    HOST_ARCH = StaticConfig(norm_arch(HOST_ARCH)),
    HOST_BITS = StaticConfig(norm_bits(HOST_BITS)),

    TARGET_ARCH = StaticConfig(norm_arch(TARGET_ARCH)),
    TARGET_BITS = StaticConfig(norm_bits(TARGET_BITS)),
  )

TEST_FORMAT = (
  '%(BUILD_CONFIG)s-'
  '%(HOST_PLATFORM)s.%(HOST_ARCH)s.%(HOST_BITS)s'
  '-to-'
  '%(TARGET_ARCH)s.%(TARGET_BITS)s'
)

# Used by the test harness to inspect and generate permutations for this
# config module.  {varname -> [possible values]}
VAR_TEST_MAP = {
  'HOST_PLATFORM':   ('linux', 'win', 'mac'),
  'HOST_ARCH':       ('intel', None),
  'HOST_BITS':       (32, 64),

  'TARGET_ARCH':     ('intel', 'arm', 'mips', None),
  'TARGET_BITS':     (32, 64, None),

  'BUILD_CONFIG':    ('Debug', 'Release'),
}
config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_FORMAT)


@config_ctx(is_root=True)
def BASE(c):
  if not (c.HOST_ARCH and c.HOST_BITS):
    raise BadConf(
        '"%s" requires host arch and bits to be set' % c.HOST_PLATFORM)
  if not (c.TARGET_ARCH and c.TARGET_BITS):
    raise BadConf('Target arch and bits must be set')
  if c.HOST_PLATFORM not in ('win', 'linux', 'mac'):  # pragma: no cover
    raise BadConf('Cannot build on "%s"' % c.HOST_PLATFORM)
  if c.HOST_BITS < c.TARGET_BITS:
    raise BadConf('Invalid config: host bits < targ bits')
  if (c.TARGET_ARCH in ('arm', 'mips') and
      c.HOST_PLATFORM != 'linux'):
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_ARCH, c.HOST_PLATFORM))

@config_ctx()
def v8(c):
  if c.TARGET_ARCH == 'arm':
    v8_target_arch = 'arm'
  elif c.TARGET_ARCH == 'mips':
    v8_target_arch = 'mips'
  elif c.TARGET_BITS == 64:
    v8_target_arch = 'x64'
  else:
    v8_target_arch = 'ia32'
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = v8_target_arch
