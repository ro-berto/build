# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import BadConf

from RECIPE_MODULES.build.chromium import CONFIG_CTX


@CONFIG_CTX(includes=['ninja', 'default_compiler'])
def libyuv(c):
  _libyuv_common(c)

  # Workaround to avoid getting goma-clang change since we can no longer use
  # the 'chromium' config above (see libyuv:677).
  if c.compile_py.compiler == 'clang':
    c.compile_py.compiler = 'goma-clang'

  c.runtests.memory_tests_runner = c.CHECKOUT_PATH.join(
      'tools_libyuv', 'valgrind', 'libyuv_tests',
      platform_ext={'win': '.bat', 'mac': '.sh', 'linux': '.sh'})

@CONFIG_CTX(includes=['chromium_clang'])
def libyuv_clang(c):
  _libyuv_common(c)
  # TODO(https://bugs.chromium.org/p/libyuv/issues/detail?id=883): After
  # switching to absl/flags, component builds are not working correctly
  # see crbug.com/1166430 for a way to fix.
  _libyuv_static_build(c)


@CONFIG_CTX(includes=['ninja', 'gcc', 'goma'])
def libyuv_gcc(c):
  _libyuv_common(c)


@CONFIG_CTX(includes=['ninja'])
def libyuv_msvc(c):
  _libyuv_common(c)
  c.gn_args.append('is_clang=false')


@CONFIG_CTX(includes=['android'])
def libyuv_android(c):
  if c.TARGET_ARCH == 'intel' and c.TARGET_BITS == 32:
    c.gn_args.append('android_full_debug=true')

  _libyuv_static_build(c)

@CONFIG_CTX(includes=['chromium'])
def libyuv_ios(c):
  if c.HOST_PLATFORM != 'mac':
    raise BadConf('Only "mac" host platform is supported for iOS (got: "%s")' %
                  c.HOST_PLATFORM)  # pragma: no cover
  if c.TARGET_PLATFORM != 'ios':
    raise BadConf('Only "ios" target platform is supported (got: "%s")' %
                  c.TARGET_PLATFORM)  # pragma: no cover
  c.build_config_fs = c.BUILD_CONFIG + '-iphoneos'

  c.gn_args.append('ios_enable_code_signing=false')
  c.gn_args.append('target_os="%s"' % c.TARGET_PLATFORM)
  _libyuv_common(c)
  _libyuv_static_build(c)

def _libyuv_common(c):
  c.compile_py.default_targets = []

def _libyuv_static_build(c):
  # TODO(kjellander): Investigate moving this into chromium recipe module's
  # static_library config instead.
  if c.BUILD_CONFIG == 'Debug':
    # GN defaults to component builds for Debug, but some build configurations
    # (Android and iOS) needs it to be static.
    c.gn_args.append('is_component_build=false')
