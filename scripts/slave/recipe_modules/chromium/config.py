# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pipes

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Dict, List, Single, Static, Set, BadConf
from recipe_engine.config_types import Path

# Because of the way that we use decorators, pylint can't figure out the proper
# type signature of functions annotated with the @config_ctx decorator.
# pylint: disable=E1123

HOST_PLATFORMS = ('linux', 'win', 'mac')
TARGET_PLATFORMS = HOST_PLATFORMS + ('ios', 'android', 'chromeos', 'fuchsia')
HOST_TARGET_BITS = (32, 64)
HOST_ARCHS = ('intel',)
TARGET_ARCHS = HOST_ARCHS + ('arm', 'mips', 'mipsel')
TARGET_CROS_BOARDS = (None, 'x86-generic')
BUILD_CONFIGS = ('Release', 'Debug', 'Coverage')
PROJECT_GENERATORS = ('gyp', 'gn', 'mb')

def check(val, potentials):
  assert val in potentials, (val, potentials)
  return val

# Schema for config items in this module.
def BaseConfig(HOST_PLATFORM, HOST_ARCH, HOST_BITS,
               TARGET_PLATFORM, TARGET_ARCH, TARGET_BITS,
               BUILD_CONFIG, TARGET_CROS_BOARD,
               CHECKOUT_PATH, **_kwargs):
  equal_fn = lambda tup: ('%s=%s' % (tup[0], pipes.quote(str(tup[1]))))
  return ConfigGroup(
    compile_py = ConfigGroup(
      default_targets = Set(basestring),
      build_args = List(basestring),
      compiler = Single(basestring, required=False),
      mode = Single(basestring, required=False),
      goma_dir = Single(Path, required=False),
      goma_client_type = Single(basestring, required=False),
      goma_use_local = Single(bool, empty_val=False, required=False),
      show_ninja_stats = Single(bool, empty_val=False, required=False),
      goma_hermetic = Single(basestring, required=False),
      goma_failfast = Single(bool, empty_val=False, required=False),
      goma_max_active_fail_fallback_tasks = Single(int, empty_val=None,
                                                   required=False),
      goma_enable_localoutputcache = Single(bool, empty_val=False,
                                            required=False),
      goma_enable_localoutputcache_small = Single(bool, empty_val=False,
                                                  required=False),
      goma_enable_global_file_stat_cache = Single(bool, empty_val=False,
                                                  required=False),
      ninja_confirm_noop = Single(bool, empty_val=False, required=False),
      # TODO(tandrii): delete goma_high_parallel from here and use goma recipe
      # module property, configured per builder in cr-buildbucket.cfg.
      goma_high_parallel = Single(bool, empty_val=False, required=False),
      use_autoninja = Single(bool, empty_val=False, required=False),
    ),
    gyp_env = ConfigGroup(
      DOWNLOAD_VR_TEST_APKS = Single(int, required=False),
      GYP_DEFINES = Dict(equal_fn, ' '.join, (basestring,int,Path)),
      GYP_MSVS_VERSION = Single(basestring, required=False),
    ),
    # This allows clients to opt out of using GYP variables in the environment.
    # TODO(machenbach): This does not expand to Chromium's runtests yet.
    use_gyp_env = Single(bool, empty_val=True, required=False),
    env = ConfigGroup(
      PATH = List(Path),
      LLVM_FORCE_HEAD_REVISION = Single(basestring, required=False),
      GOMA_STUBBY_PROXY_IP_ADDRESS = Single(basestring, required=False),
      GOMA_RPC_EXTRA_PARAMS = Single(basestring, required=False),
      GOMA_SETTINGS_SERVER = Single(basestring, required=False),
      GOMA_USE_CASE = Single(basestring, required=False),
      GOMA_LOCAL_OUTPUT_CACHE_MAX_CACHE_AMOUNT_IN_MB = Single(int,
                                                              required=False),
      GOMA_LOCAL_OUTPUT_CACHE_THRESHOLD_CACHE_AMOUNT_IN_MB = Single(
          int, required=False),
      FORCE_MAC_TOOLCHAIN = Single(int, required=False),
    ),
    mac_toolchain = ConfigGroup(
      enabled = Single(bool, empty_val=False, required=False),
      # The build version of Xcode itself. Update its value to change the Xcode
      # version.
      xcode_build_version = Single(basestring),
      # Xcode installer configs. These normally don't change with Xcode version.
      installer_cipd_package = Single(basestring),
      installer_version = Single(basestring),
      installer_cmd = Single(basestring),
      # CIPD cannot distribute Xcode publicly, hence its package requires
      # credentials on buildbot slaves. LUCI bots should NOT set this var, to
      # let CIPD use credentials from the LUCI context.
      cipd_credentials = Single(basestring, required=False),
    ),
    project_generator = ConfigGroup(
      tool = Single(basestring, empty_val='mb'),
      config_path = Single(Path),
      args = Set(basestring),
      isolate_map_paths = List(Path),
    ),
    build_dir = Single(Path),
    cros_sdk = ConfigGroup(
      external = Single(bool, empty_val=True, required=False),
      args = List(basestring),
    ),
    runtests = ConfigGroup(
      enable_memcheck = Single(bool, empty_val=False, required=False),
      memory_tests_runner = Single(Path),
      enable_asan = Single(bool, empty_val=False, required=False),
      enable_lsan = Single(bool, empty_val=False, required=False),
      enable_msan = Single(bool, empty_val=False, required=False),
      enable_tsan = Single(bool, empty_val=False, required=False),
      test_args = List(basestring),
      run_asan_test = Single(bool, required=False),
    ),

    # Some platforms do not have a 1:1 correlation of BUILD_CONFIG to what is
    # passed as --target on the command line.
    build_config_fs = Single(basestring),

    BUILD_CONFIG = Static(check(BUILD_CONFIG, BUILD_CONFIGS)),

    HOST_PLATFORM = Static(check(HOST_PLATFORM, HOST_PLATFORMS)),
    HOST_ARCH = Static(check(HOST_ARCH, HOST_ARCHS)),
    HOST_BITS = Static(check(HOST_BITS, HOST_TARGET_BITS)),

    TARGET_PLATFORM = Static(check(TARGET_PLATFORM, TARGET_PLATFORMS)),
    TARGET_ARCH = Static(check(TARGET_ARCH, TARGET_ARCHS)),
    TARGET_BITS = Static(check(TARGET_BITS, HOST_TARGET_BITS)),
    TARGET_CROS_BOARD = Static(TARGET_CROS_BOARD),

    CHECKOUT_PATH = Static(CHECKOUT_PATH),

    gn_args = List(basestring),

    clobber_before_runhooks = Single(bool, empty_val=False,
                                     required=False, hidden=False),
  )

config_ctx = config_item_context(BaseConfig)


@config_ctx(is_root=True)
def BASE(c):
  host_targ_tuples = [(c.HOST_PLATFORM, c.HOST_ARCH, c.HOST_BITS),
                      (c.TARGET_PLATFORM, c.TARGET_ARCH, c.TARGET_BITS)]

  for (plat, arch, bits) in host_targ_tuples:
    if plat == 'ios':
      if arch not in ('arm', 'intel'):  # pragma: no cover
        raise BadConf('%s/%s arch is not supported on %s' % (arch, bits, plat))
    elif plat in ('win', 'mac'):
      if arch != 'intel':  # pragma: no cover
        raise BadConf('%s arch is not supported on %s' % (arch, plat))
    elif plat in ('chromeos', 'android', 'linux', 'fuchsia'):
      pass  # no arch restrictions
    else:  # pragma: no cover
      assert False, "Not covering a platform: %s" % plat

  potential_platforms = {
    # host -> potential target platforms
    'win':   ('win',),
    'mac':   ('mac', 'ios'),
    'linux': ('linux', 'chromeos', 'android', 'fuchsia', 'win'),
  }.get(c.HOST_PLATFORM)

  if not potential_platforms:  # pragma: no cover
    raise BadConf('Cannot build on "%s"' % c.HOST_PLATFORM)

  if c.TARGET_PLATFORM not in potential_platforms:
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))  # pragma: no cover

  if c.TARGET_CROS_BOARD:
    if not c.TARGET_PLATFORM == 'chromeos':  # pragma: no cover
      raise BadConf("Cannot specify CROS board for non-'chromeos' platform")

  if c.HOST_BITS < c.TARGET_BITS:
    raise BadConf('host bits < targ bits')  # pragma: no cover

  c.build_config_fs = c.BUILD_CONFIG
  if c.HOST_PLATFORM == 'win':
    if c.TARGET_BITS == 64:
      # Windows requires 64-bit builds to be in <dir>_x64.
      c.build_config_fs = c.BUILD_CONFIG + '_x64'

  # Test runner memory tools that are not compile-time based.
  c.runtests.memory_tests_runner = c.CHECKOUT_PATH.join(
      'tools', 'valgrind', 'chrome_tests',
      platform_ext={'win': '.bat', 'mac': '.sh', 'linux': '.sh'})

  if c.project_generator.tool not in PROJECT_GENERATORS:  # pragma: no cover
    raise BadConf('"%s" is not a supported project generator tool, the '
                  'supported ones are: %s' % (c.project_generator.tool,
                                              ','.join(PROJECT_GENERATORS)))
  gyp_arch = {
    ('intel', 32): 'ia32',
    ('intel', 64): 'x64',
    ('arm',   32): 'arm',
    ('arm',   64): 'arm64',
    ('mips',  32): 'mips',
    ('mips',  64): 'mips64',
    ('mipsel',  32): 'mipsel',
    ('mipsel',  64): 'mips64el',
  }.get((c.TARGET_ARCH, c.TARGET_BITS))
  if gyp_arch:
    c.gyp_env.GYP_DEFINES['target_arch'] = gyp_arch

  if c.HOST_PLATFORM == 'mac':
    c.mac_toolchain.xcode_build_version = '9C40b'
    c.mac_toolchain.installer_cipd_package = (
        'infra/tools/mac_toolchain/${platform}')
    c.mac_toolchain.installer_version = (
        'git_revision:796d2b92cff93fc2059623ce0a66284373ceea0a')
    c.mac_toolchain.installer_cmd = 'mac_toolchain'
    # TODO(crbug.com/790154): make this conditional, do not set for LUCI bots.
    c.mac_toolchain.cipd_credentials = (
        '/creds/service_accounts/service-account-xcode-cipd-access.json')

  # TODO(sergeyberezin): remove this when all builds switch to the new Xcode
  # flow.
  if c.TARGET_PLATFORM == 'mac':
    c.env.FORCE_MAC_TOOLCHAIN = 1

  if c.BUILD_CONFIG not in ['Coverage', 'Release', 'Debug']: # pragma: no cover
    raise BadConf('Unknown build config "%s"' % c.BUILD_CONFIG)

@config_ctx()
def gn(c):
  c.project_generator.tool = 'gn'

@config_ctx()
def mb(c):
  c.project_generator.tool = 'mb'

@config_ctx()
def win_analyze(c):
  c.gyp_env.GYP_DEFINES['use_goma'] = 0  # Read by api.py.

@config_ctx(group='builder')
def ninja(c):
  out_path = 'out'
  if c.TARGET_CROS_BOARD:
    out_path += '_%s' % (c.TARGET_CROS_BOARD,)
  c.build_dir = c.CHECKOUT_PATH.join(out_path)

@config_ctx()
def goma_failfast(c):
  c.compile_py.goma_failfast = True

@config_ctx()
def goma_high_parallel(c):
  c.compile_py.goma_high_parallel = True

@config_ctx()
def goma_enable_global_file_stat_cache(c):
  # Do not enable this if some src files are modified for recompilation
  # while running goma daemon.
  c.compile_py.goma_enable_global_file_stat_cache = True

@config_ctx()
def goma_canary(c):
  c.compile_py.goma_client_type = 'candidate'
  c.compile_py.goma_hermetic = 'error'
  c.compile_py.goma_failfast = True
  c.compile_py.show_ninja_stats = True

@config_ctx()
def goma_latest_client(c):
  c.compile_py.goma_client_type = 'latest'
  c.compile_py.goma_hermetic = 'error'
  c.compile_py.goma_failfast = True
  c.compile_py.show_ninja_stats = True

@config_ctx()
def goma_staging(c):
  c.compile_py.goma_failfast = True
  c.env.GOMA_STUBBY_PROXY_IP_ADDRESS = 'sandbox.google.com'
  c.compile_py.ninja_confirm_noop = True

@config_ctx()
def goma_rbe_tot(c):
  c.compile_py.goma_failfast = True
  c.env.GOMA_SETTINGS_SERVER = (
      'https://cxx-compiler-service.appspot.com/settings')
  c.env.GOMA_USE_CASE = 'rbe-tot'
  c.compile_py.use_autoninja = True

@config_ctx()
def goma_mixer_staging(c):
  c.compile_py.goma_failfast = True
  c.env.GOMA_STUBBY_PROXY_IP_ADDRESS = 'staging-goma.chromium.org'
  c.env.GOMA_RPC_EXTRA_PARAMS = '?staging'
  c.compile_py.use_autoninja = True

# TODO(ukai): add goma_mixer_prod

@config_ctx()
def goma_rbe_prod(c):
  c.compile_py.goma_failfast = True
  c.env.GOMA_SETTINGS_SERVER = (
      'https://cxx-compiler-service.appspot.com/settings')
  c.env.GOMA_USE_CASE = 'rbe-prod'
  c.compile_py.use_autoninja = True

@config_ctx()
def goma_hermetic_fallback(c):
  c.compile_py.goma_hermetic = 'fallback'

@config_ctx()
def goma_localoutputcache(c):
  c.compile_py.goma_enable_localoutputcache = True

@config_ctx()
def goma_localoutputcache_small(c):
  c.compile_py.goma_enable_localoutputcache = True
  c.env.GOMA_LOCAL_OUTPUT_CACHE_MAX_CACHE_AMOUNT_IN_MB = 10*1024
  c.env.GOMA_LOCAL_OUTPUT_CACHE_THRESHOLD_CACHE_AMOUNT_IN_MB = 5*1024

@config_ctx()
def goma_use_local(c):
  c.compile_py.goma_use_local = True

@config_ctx()
def ninja_confirm_noop(c):
  c.compile_py.ninja_confirm_noop = True

@config_ctx()
def use_autoninja(c):
  c.compile_py.use_autoninja = True

@config_ctx(group='builder')
def xcode(c):  # pragma: no cover
  if c.HOST_PLATFORM != 'mac':
    raise BadConf('can not use xcodebuild on "%s"' % c.HOST_PLATFORM)

def _clang_common(c):
  c.compile_py.compiler = 'clang'
  c.gn_args.append('is_clang=true')
  c.gyp_env.GYP_DEFINES['clang'] = 1  # Read by api.py.

@config_ctx(group='compiler')
def clang(c):
  _clang_common(c)

@config_ctx(group='compiler')
def gcc(c):
  c.gn_args.append('is_clang=false')
  c.gyp_env.GYP_DEFINES['clang'] = 0  # Read by api.py.

@config_ctx(group='compiler')
def default_compiler(c):
  if c.TARGET_PLATFORM in ('mac', 'ios'):
    _clang_common(c)

@config_ctx(deps=['compiler', 'builder'], group='distributor')
def goma(c):
  if not c.compile_py.compiler:
    c.compile_py.compiler = 'goma'
  elif c.compile_py.compiler == 'clang':
    c.compile_py.compiler = 'goma-clang'
  else:  # pragma: no cover
    raise BadConf('goma config doesn\'t understand %s' % c.compile_py.compiler)

  if c.TARGET_PLATFORM == 'win' and c.compile_py.compiler != 'goma-clang':
    fastbuild(c)

@config_ctx()
def dcheck(c, invert=False):
  c.gn_args.append('dcheck_always_on=%s' % str(not invert).lower())

@config_ctx()
def fastbuild(c, invert=False):
  c.gn_args.append('symbol_level=%d' % (1 if invert else 2))

@config_ctx()
def clobber(c):
  c.clobber_before_runhooks = True

@config_ctx(includes=['clobber'])
def official(c):
  c.compile_py.mode = 'official'

@config_ctx(deps=['compiler'])
def analysis(c):
  c.gn_args.append('use_clang_static_analyzer=true')

@config_ctx(deps=['compiler'])
def asan(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('asan requires clang')
  c.runtests.enable_asan = True
  if c.TARGET_PLATFORM in ['mac', 'win']:
    # Set fastbuild=0 and prevent other configs from changing it.
    fastbuild(c, invert=True, optional=False)

  c.gn_args.append('is_asan=true')
  if c.TARGET_PLATFORM not in ('android', 'mac') and c.TARGET_BITS == 64:
    # LSAN isn't supported on Android, Mac or 32 bits platforms.
    c.gn_args.append('is_lsan=true')

@config_ctx(deps=['compiler'])
def lsan(c):
  c.runtests.enable_lsan = True

@config_ctx(deps=['compiler'])
def msan(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('msan requires clang')
  c.runtests.enable_msan = True
  c.gn_args.append('is_msan=true')

@config_ctx(deps=['compiler'])
def ubsan(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('ubsan requires clang')
  c.gn_args.append('is_ubsan=true')

@config_ctx(deps=['compiler'])
def ubsan_vptr(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('ubsan_vptr requires clang')
  c.gn_args.append('is_ubsan_vptr=true')

@config_ctx(group='memory_tool')
def memcheck(c):
  c.runtests.enable_memcheck = True

@config_ctx(deps=['compiler'], group='memory_tool')
def tsan2(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('tsan2 requires clang')
  c.runtests.enable_tsan = True
  c.gn_args.append('is_tsan=true')

@config_ctx()
def trybot_flavor(c):
  fastbuild(c, optional=True)
  dcheck(c, optional=True)

@config_ctx()
def clang_tot(c):
  c.env.LLVM_FORCE_HEAD_REVISION = 'YES'

#### 'Full' configurations

@config_ctx(includes=['ninja', 'clang', 'asan'])
def win_asan(_):
  pass

@config_ctx(includes=['ninja', 'default_compiler'])
def chromium_no_goma(c):
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['ninja', 'default_compiler', 'goma'])
def chromium(c):
  c.compile_py.default_targets = ['all']
  c.cros_sdk.external = True

@config_ctx(includes=['ninja', 'clang', 'goma'])
def chromium_win_clang(c):
  fastbuild(c, final=False)  # final=False so win_clang_asan can override it.

@config_ctx(includes=['ninja', 'clang', 'clang_tot'])  # No goma.
def chromium_win_clang_tot(c):
  fastbuild(c)

@config_ctx(includes=['chromium_win_clang', 'official'])
def chromium_win_clang_official(_):
  pass

@config_ctx(includes=['chromium_win_clang_tot', 'official'])
def chromium_win_clang_official_tot(_):
  pass

@config_ctx(includes=['win_asan', 'goma'])
def chromium_win_clang_asan(_):
  pass

@config_ctx(includes=['win_asan', 'clang_tot'])  # No goma.
def chromium_win_clang_asan_tot(_):
  pass

@config_ctx(includes=['ninja', 'clang', 'clang_tot'])  # No goma.
def clang_tot_linux(_):
  pass

@config_ctx(includes=['ninja', 'clang', 'clang_tot'])  # No goma.
def clang_tot_mac(c):
  fastbuild(c, final=False)  # final=False so clang_tot_mac_asan can override.

@config_ctx(includes=['clang_tot_linux', 'asan'])
def clang_tot_linux_asan(_):
  pass

@config_ctx(includes=['ninja', 'clang', 'goma', 'clobber',
                      'ubsan'])
def chromium_linux_ubsan(_):
  pass

@config_ctx(includes=['ninja', 'clang', 'goma', 'clobber',
                      'ubsan_vptr'])
def chromium_linux_ubsan_vptr(_):
  pass

@config_ctx(includes=['clang_tot_linux', 'ubsan_vptr'])
def clang_tot_linux_ubsan_vptr(_):
  pass

@config_ctx(includes=['clang_tot_mac', 'asan'])
def clang_tot_mac_asan(_):
  pass

@config_ctx(includes=['android_common', 'ninja', 'clang', 'clang_tot'])
def clang_tot_android(_):
  pass

@config_ctx(includes=['clang_tot_android', 'asan'])
def clang_tot_android_asan(_):
  # Like android_clang, minus goma, minus static_libarary, plus asan.
  pass

@config_ctx(includes=['clang_tot_android'])
def clang_tot_android_dbg(_):
  # Like android_clang, minus goma, minus static_libarary.
  pass

# GYP_DEFINES must not include 'asan' or 'clang', else the tester bot will try
# to compile clang.
@config_ctx(includes=['chromium_no_goma'])
def chromium_win_asan(c):
  c.runtests.run_asan_test = True

@config_ctx(includes=['ninja', 'clang', 'goma', 'asan'])
def chromium_asan(c): # pragma: no cover
  # Used by some bots in chromium_tests/chromium_fuzz.py.
  del c

@config_ctx(includes=['ninja', 'clang', 'goma', 'msan'])
def chromium_msan(c):
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['ninja', 'clang', 'goma', 'tsan2'])
def chromium_tsan2(c):
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['ninja', 'default_compiler', 'goma'])
def chromium_chromeos(c):  # pragma: no cover
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['ninja', 'clang', 'goma'])
def chromium_chromeos_clang(c):  # pragma: no cover
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['ninja', 'clang', 'goma'])
def chromium_clang(c):
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['chromium', 'official'])
def chromium_official(c):
  # TODO(phajdan.jr): Unify compile targets used by official builders.
  if c.TARGET_PLATFORM == 'win':
    c.compile_py.default_targets = ['chrome_official_builder']
  elif c.TARGET_PLATFORM in ['linux', 'mac']:
    c.compile_py.default_targets = []

@config_ctx(includes=['chromium_official'])
def chromium_official_internal(c):
   # TODO(mmoss): This isn't right, since CHECKOUT_PATH is the directory that
   # the primary solution (i.e. 'src') is checked out to, but we need the
   # top-level, .gclient path.
  c.project_generator.config_path = c.CHECKOUT_PATH.join(
      'src-internal', 'tools', 'mb', 'mb_config.pyl')

# TODO(phajdan.jr): cover or remove blink; used by blink_downstream.
@config_ctx(includes=['chromium'])
def blink(c):  # pragma: no cover
  c.compile_py.default_targets = ['blink_tests']

@config_ctx(includes=['android_common', 'ninja', 'default_compiler', 'goma'])
def android(_):
  pass

@config_ctx(includes=['android_common', 'ninja', 'clang',
                      'goma'])
def android_clang(_):
  pass

@config_ctx(includes=['android_common', 'ninja', 'clang',
                      'goma', 'asan'])
def android_asan(_):
  pass

@config_ctx()
def android_common(c):
  c.env.PATH.extend([
      c.CHECKOUT_PATH.join(
          'third_party', 'android_tools', 'sdk', 'platform-tools'),
      c.CHECKOUT_PATH.join('build', 'android')])

@config_ctx(includes=['ninja', 'clang', 'goma'])
def codesearch(c):
  # -k 0 prevents stopping on errors, so the compile step tries to do as much as
  # possible.
  c.compile_py.build_args = ['-k' ,'0']

@config_ctx()
def download_vr_test_apks(c):
  c.gyp_env.DOWNLOAD_VR_TEST_APKS = 1

@config_ctx()
def mac_toolchain(c, xcode_build_version=None):
  if c.HOST_PLATFORM != 'mac': # pragma: no cover
    raise BadConf('Cannot setup Xcode on "%s"' % c.HOST_PLATFORM)

  c.mac_toolchain.enabled = True
  if xcode_build_version: # pragma: no cover
    c.mac_toolchain.xcode_build_version = xcode_build_version
  # TODO(crbug.com/797051): remove this when all builds switch to the new Xcode
  # flow.
  c.env.FORCE_MAC_TOOLCHAIN = 0

@config_ctx(includes=['mb'])
def android_internal_isolate_maps(c):
  c.project_generator.isolate_map_paths = [
      c.CHECKOUT_PATH.join('clank', 'build', 'gn_isolate_map.pyl'),
      c.CHECKOUT_PATH.join('testing', 'buildbot', 'gn_isolate_map.pyl'),
  ]
