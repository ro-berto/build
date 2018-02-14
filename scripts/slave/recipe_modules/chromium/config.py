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
               BUILD_PATH, CHECKOUT_PATH, **_kwargs):
  equal_fn = lambda tup: ('%s=%s' % (tup[0], pipes.quote(str(tup[1]))))
  return ConfigGroup(
    compile_py = ConfigGroup(
      default_targets = Set(basestring),
      build_args = List(basestring),
      compiler = Single(basestring, required=False),
      mode = Single(basestring, required=False),
      goma_dir = Single(Path, required=False),
      goma_canary = Single(bool, empty_val=False, required=False),
      show_ninja_stats = Single(bool, empty_val=False, required=False),
      goma_hermetic = Single(basestring, required=False),
      goma_failfast = Single(bool, empty_val=False, required=False),
      goma_connection_retry = Single(bool, empty_val=False, required=False),
      goma_max_active_fail_fallback_tasks = Single(int, empty_val=None, required=False),
      goma_enable_localoutputcache = Single(bool, empty_val=False, required=False),
      goma_enable_global_file_id_cache = Single(bool, empty_val=False, required=False),
      ninja_confirm_noop = Single(bool, empty_val=False, required=False),
      set_build_data_dir = Single(bool, empty_val=False, required=False),
      # TODO(tandrii): delete goma_high_parallel from here and use goma recipe
      # module property, configured per builder in cr-buildbucket.cfg.
      goma_high_parallel = Single(bool, empty_val=False, required=False),
    ),
    runtest_py = ConfigGroup(
      src_side = Single(bool),
    ),
    gyp_env = ConfigGroup(
      DOWNLOAD_VR_TEST_APKS = Single(int, required=False),
      GYP_CROSSCOMPILE = Single(int, jsonish_fn=str, required=False),
      GYP_DEFINES = Dict(equal_fn, ' '.join, (basestring,int,Path)),
      GYP_GENERATORS = Set(basestring, ','.join),
      GYP_GENERATOR_FLAGS = Dict(equal_fn, ' '.join, (basestring,int)),
      GYP_INCLUDE_LAST = Single(Path, required=False),
      GYP_MSVS_VERSION = Single(basestring, required=False),
      GYP_USE_SEPARATE_MSPDBSRV = Single(int, jsonish_fn=str, required=False),
      LLVM_DOWNLOAD_GOLD_PLUGIN = Single(int, required=False),
    ),
    env = ConfigGroup(
      PATH = List(Path),
      ADB_VENDOR_KEYS = Single(Path, required=False),
      LLVM_FORCE_HEAD_REVISION = Single(basestring, required=False),
      GOMA_STUBBY_PROXY_IP_ADDRESS = Single(basestring, required=False),
      GOMA_SETTINGS_SERVER = Single(basestring, required=False),
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
      enable_lsan = Single(bool, empty_val=False, required=False),
      test_args = List(basestring),
      run_asan_test = Single(bool, required=False),
      swarming_extra_args = List(basestring),
      swarming_tags = Set(basestring),
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

    BUILD_PATH = Static(BUILD_PATH),
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
    'linux': ('linux', 'chromeos', 'android', 'fuchsia'),
  }.get(c.HOST_PLATFORM)

  if not potential_platforms:  # pragma: no cover
    raise BadConf('Cannot build on "%s"' % c.HOST_PLATFORM)

  if c.TARGET_PLATFORM not in potential_platforms:
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))  # pragma: no cover

  if c.TARGET_CROS_BOARD:
    if not c.TARGET_PLATFORM == 'chromeos':  # pragma: no cover
      raise BadConf("Cannot specify CROS board for non-'chromeos' platform")

  if c.HOST_PLATFORM != c.TARGET_PLATFORM or c.HOST_ARCH != c.TARGET_ARCH:
    c.gyp_env.GYP_CROSSCOMPILE = 1

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
        'git_revision:d4dc0c29a004b59dcca1e69ae84eba0c932eb010')
    c.mac_toolchain.installer_cmd = 'mac_toolchain'
    # TODO(crbug.com/790154): make this conditional, do not set for LUCI bots.
    c.mac_toolchain.cipd_credentials = (
        '/creds/service_accounts/service-account-xcode-cipd-access.json')

  # TODO(crbug.com/797051): remove this when all builds switch to the new
  # Xcode flow.
  if c.TARGET_PLATFORM == 'mac':
    c.env.FORCE_MAC_TOOLCHAIN = 1

  if c.BUILD_CONFIG in ['Coverage', 'Release']:
    # The 'Coverage' target is not explicitly used by Chrome, but by some other
    # projects in the Chrome ecosystem (ie: Syzygy).
    static_library(c, final=False)
  elif c.BUILD_CONFIG == 'Debug':
    shared_library(c, final=False)
  else:  # pragma: no cover
    raise BadConf('Unknown build config "%s"' % c.BUILD_CONFIG)

@config_ctx()
def gn(c):
  c.project_generator.tool = 'gn'

@config_ctx()
def mb(c):
  c.project_generator.tool = 'mb'

@config_ctx()
def gn_for_uploads(c):
  # This config is used to do the official builds of GN itself (which
  # are uploaded into Google Cloud Storage). While most of the configuration
  # of the build is done repo-side via MB, we need to set a few GYP_DEFINES
  # so that `gclient runhooks` will do the right thing.

  if c.TARGET_PLATFORM == 'linux':
    c.gyp_env.GYP_DEFINES['branding'] = 'Chrome'
    c.gyp_env.GYP_DEFINES['buildtype'] = 'Official'

@config_ctx()
def win_analyze(c):
  c.gyp_env.GYP_DEFINES['win_analyze'] = '1'
  c.gyp_env.GYP_DEFINES['fastbuild'] = '2'
  c.gyp_env.GYP_DEFINES['use_goma'] = 0

@config_ctx(group='builder')
def ninja(c):
  if c.TARGET_PLATFORM == 'ios':
    c.gyp_env.GYP_GENERATORS.add('ninja')

  out_path = 'out'
  if c.TARGET_CROS_BOARD:
    out_path += '_%s' % (c.TARGET_CROS_BOARD,)
  c.build_dir = c.CHECKOUT_PATH.join(out_path)

@config_ctx()
def msvs2015(c):
  c.gn_args.append('visual_studio_version=2015')
  c.gyp_env.GYP_MSVS_VERSION = '2015'

@config_ctx()
def goma_failfast(c):
  c.compile_py.goma_failfast = True

@config_ctx()
def goma_high_parallel(c):
  c.compile_py.goma_high_parallel = True

@config_ctx()
def goma_enable_global_file_id_cache(c):
  # Do not enable this if some src files are modified for recompilation
  # while running goma daemon.
  c.compile_py.goma_enable_global_file_id_cache = True

@config_ctx()
def goma_canary(c):
  c.compile_py.goma_canary = True
  c.compile_py.goma_hermetic = 'error'
  c.compile_py.goma_failfast = True
  c.compile_py.show_ninja_stats = True

@config_ctx()
def goma_staging(c):
  c.compile_py.goma_failfast = True
  c.env.GOMA_STUBBY_PROXY_IP_ADDRESS = 'sandbox.google.com'
  c.compile_py.ninja_confirm_noop = True

@config_ctx()
def goma_gce(c):
  c.compile_py.goma_failfast = True
  c.compile_py.goma_connection_retry = True
  c.env.GOMA_SETTINGS_SERVER = (
      'https://cxx-compiler-service.appspot.com/settings')

@config_ctx()
def goma_hermetic_fallback(c):
  c.compile_py.goma_hermetic = 'fallback'

@config_ctx()
def goma_localoutputcache(c):
  c.compile_py.goma_enable_localoutputcache = True

@config_ctx()
def ninja_confirm_noop(c):
  c.compile_py.ninja_confirm_noop = True

@config_ctx(group='builder')
def xcode(c):  # pragma: no cover
  if c.HOST_PLATFORM != 'mac':
    raise BadConf('can not use xcodebuild on "%s"' % c.HOST_PLATFORM)
  c.gyp_env.GYP_GENERATORS.add('xcode')

def _clang_common(c):
  c.compile_py.compiler = 'clang'
  c.gn_args.append('is_clang=true')
  c.gyp_env.GYP_DEFINES['clang'] = 1

@config_ctx(group='compiler')
def clang(c):
  _clang_common(c)

@config_ctx(group='compiler')
def gcc(c):
  c.gn_args.append('is_clang=false')
  c.gyp_env.GYP_DEFINES['clang'] = 0

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
  c.gyp_env.GYP_DEFINES['dcheck_always_on'] = int(not invert)

@config_ctx()
def fastbuild(c, invert=False):
  c.gn_args.append('symbol_level=%d' % (1 if invert else 2))
  c.gyp_env.GYP_DEFINES['fastbuild'] = int(not invert)

@config_ctx()
def no_dump_symbols(c):
  c.gyp_env.GYP_DEFINES['linux_dump_symbols'] = 0

@config_ctx()
def isolation_mode_noop(c):
  c.gyp_env.GYP_DEFINES['test_isolation_mode'] = 'noop'

@config_ctx(group='link_type')
def shared_library(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'

@config_ctx(group='link_type')
def static_library(c):
  c.gyp_env.GYP_DEFINES['component'] = 'static_library'

@config_ctx()
def ffmpeg_branding(c, branding=None):
  if branding:
    c.gyp_env.GYP_DEFINES['ffmpeg_branding'] = branding

@config_ctx()
def proprietary_codecs(c, invert=False):
  c.gyp_env.GYP_DEFINES['proprietary_codecs'] = int(not invert)

@config_ctx()
def chrome_with_codecs(c):
  ffmpeg_branding(c, branding='Chrome')
  proprietary_codecs(c)

@config_ctx()
def chromeos_with_codecs(c):
  ffmpeg_branding(c, branding='ChromeOS')
  proprietary_codecs(c)

@config_ctx()
def chromiumos(c):
  c.gyp_env.GYP_DEFINES['chromeos'] = 1

@config_ctx(includes=['chromiumos'])
def chromeos(c):
  ffmpeg_branding(c, branding='ChromeOS')
  proprietary_codecs(c)

@config_ctx()
def ozone(c):
  c.gyp_env.GYP_DEFINES['use_ozone'] = 1

@config_ctx()
def clobber(c):
  c.clobber_before_runhooks = True

@config_ctx(includes=['static_library', 'clobber'])
def official(c):
  c.gyp_env.GYP_DEFINES['branding'] = 'Chrome'
  c.gyp_env.GYP_DEFINES['buildtype'] = 'Official'
  c.compile_py.mode = 'official'

@config_ctx(deps=['compiler'])
def analysis(c):
  c.gn_args.append('use_clang_static_analyzer=true')

@config_ctx(deps=['compiler'])
def asan(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('asan requires clang')
  c.runtests.swarming_tags |= {'asan:1'}
  if c.TARGET_PLATFORM in ['mac', 'win']:
    # Set fastbuild=0 and prevent other configs from changing it.
    fastbuild(c, invert=True, optional=False)

  c.gn_args.append('is_asan=true')
  c.gyp_env.GYP_DEFINES['asan'] = 1
  if c.TARGET_PLATFORM not in ('android', 'mac') and c.TARGET_BITS == 64:
    # LSAN isn't supported on Android, Mac or 32 bits platforms.
    c.gn_args.append('is_lsan=true')
    c.gyp_env.GYP_DEFINES['lsan'] = 1

@config_ctx(deps=['compiler'])
def lsan(c):
  c.runtests.enable_lsan = True
  c.runtests.swarming_extra_args += ['--lsan=1']
  c.runtests.swarming_tags |= {'lsan:1'}

# TODO(infra,earthdok,glider): Make this a gyp variable. This is also not a
# good name as only v8 builds release symbolized with -O2 while
# chromium.lkgr uses -O1.
@config_ctx()
def asan_symbolized(c):
  c.gyp_env.GYP_DEFINES['release_extra_cflags'] = (
      '-fno-inline-functions -fno-inline')

@config_ctx()
def sanitizer_coverage(c):
  c.gyp_env.GYP_DEFINES['sanitizer_coverage'] = 'trace-pc-guard'

@config_ctx(deps=['compiler'])
def msan(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('msan requires clang')
  c.runtests.swarming_tags |= {'msan:1'}
  c.gn_args.append('is_msan=true')
  c.gyp_env.GYP_DEFINES['msan'] = 1

@config_ctx()
def msan_no_origin_tracking(c):
  # Don't track the chain of stores leading from allocation site to use site.
  c.gyp_env.GYP_DEFINES['msan_track_origins'] = 0

@config_ctx()
def msan_full_origin_tracking(c):
  # Track the chain of stores leading from allocation site to use site.
  c.gyp_env.GYP_DEFINES['msan_track_origins'] = 2

# This is currently needed to make tests return a non-zero exit code when an
# UBSan failure happens.
# TODO(kjellander,samsonov): Remove when the upstream bug
# (https://llvm.org/bugs/show_bug.cgi?id=25569) is fixed.
@config_ctx()
def ubsan_fail_on_errors(c):
  c.gyp_env.GYP_DEFINES['release_extra_cflags'] = (
      '-fno-sanitize-recover=undefined')

@config_ctx(deps=['compiler'], includes=['ubsan_fail_on_errors'])
def ubsan(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('ubsan requires clang')
  c.gn_args.append('is_ubsan=true')
  c.gyp_env.GYP_DEFINES['ubsan'] = 1

@config_ctx(deps=['compiler'], includes=['ubsan_fail_on_errors'])
def ubsan_vptr(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('ubsan_vptr requires clang')
  c.gn_args.append('is_ubsan_vptr=true')
  c.gyp_env.GYP_DEFINES['ubsan_vptr'] = 1

@config_ctx()
def prebuilt_instrumented_libraries(c):
  c.gyp_env.GYP_DEFINES['use_prebuilt_instrumented_libraries'] = 1

@config_ctx(group='memory_tool')
def memcheck(c):
  c.runtests.enable_memcheck = True
  c.gyp_env.GYP_DEFINES['build_for_tool'] = 'memcheck'

@config_ctx(deps=['compiler'], group='memory_tool')
def tsan2(c):
  if 'clang' not in c.compile_py.compiler:  # pragma: no cover
    raise BadConf('tsan2 requires clang')
  c.runtests.swarming_tags |= {'tsan:1'}
  c.gn_args.append('is_tsan=true')
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['tsan'] = 1
  gyp_defs['disable_nacl'] = 1

@config_ctx()
def syzyasan_compile_only(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['syzyasan'] = 1
  gyp_defs['win_z7'] = 0

@config_ctx(
    deps=['compiler'], group='memory_tool', includes=['syzyasan_compile_only'])
def syzyasan(c):
  if c.gyp_env.GYP_DEFINES['component'] != 'static_library':  # pragma: no cover
    raise BadConf('SyzyASan requires component=static_library')
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['win_z7'] = 1
  gyp_defs['chromium_win_pch'] = 0

@config_ctx()
def trybot_flavor(c):
  fastbuild(c, optional=True)
  dcheck(c, optional=True)

@config_ctx()
def clang_tot(c):
  c.env.LLVM_FORCE_HEAD_REVISION = 'YES'
  # Plugin flags often need to be changed when using a plugin newer than
  # the latest Clang package, so disable plugins.
  # TODO(pcc): Investigate whether this should be consistent between Windows and
  # non-Windows.
  if c.TARGET_PLATFORM != 'win':
    c.gyp_env.GYP_DEFINES['clang_use_chrome_plugins'] = 0

@config_ctx(includes=['ninja', 'clang', 'asan', 'static_library'])
def win_asan(c):
  c.gyp_env.GYP_DEFINES['enable_ipc_fuzzer'] = 1
  c.gyp_env.GYP_DEFINES['v8_enable_verify_heap'] = 1

#### 'Full' configurations
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
def chromium_win_clang_official(c):
  pass

@config_ctx(includes=['chromium_win_clang_tot', 'official'])
def chromium_win_clang_official_tot(c):
  pass

@config_ctx(includes=['win_asan', 'goma'])
def chromium_win_clang_asan(c):
  pass

@config_ctx(includes=['win_asan', 'clang_tot'])  # No goma.
def chromium_win_clang_asan_tot(c):
  pass

@config_ctx(includes=['chromium_win_clang_asan_tot', 'sanitizer_coverage'])
def chromium_win_clang_asan_tot_coverage(c):
  pass

@config_ctx(includes=['ninja', 'clang', 'clang_tot'])  # No goma.
def clang_tot_linux(c):
  pass

@config_ctx(includes=['ninja', 'clang', 'clang_tot'])  # No goma.
def clang_tot_mac(c):
  fastbuild(c, final=False)  # final=False so clang_tot_mac_asan can override.

@config_ctx()
def asan_test_batch(c):
  c.runtests.test_args.append('--test-launcher-batch-limit=1')

@config_ctx(includes=['clang_tot_linux', 'asan', 'chromium_sanitizer',
                      'asan_test_batch'])
def clang_tot_linux_asan(c):
  # Like chromium_linux_asan, without goma.
  pass

@config_ctx(includes=['ninja', 'clang', 'goma', 'clobber',
                      'ubsan', 'sanitizer_coverage'])
def chromium_linux_ubsan(c):
  pass

@config_ctx(includes=['ninja', 'clang', 'goma', 'clobber',
                      'ubsan_vptr', 'sanitizer_coverage'])
def chromium_linux_ubsan_vptr(c):
  pass

@config_ctx(includes=['clang_tot_linux', 'ubsan_vptr', 'sanitizer_coverage'])
def clang_tot_linux_ubsan_vptr(c):
  pass

@config_ctx(includes=['clang_tot_mac', 'asan', 'chromium_sanitizer',
            'static_library'])
def clang_tot_mac_asan(c):
  pass

@config_ctx(includes=['android_common', 'ninja', 'clang', 'clang_tot'])
def clang_tot_android(c):
  pass

@config_ctx(includes=['clang_tot_android', 'asan'])
def clang_tot_android_asan(c):
  # Like android_clang, minus goma, minus static_libarary, plus asan.
  pass

@config_ctx(includes=['clang_tot_android'])
def clang_tot_android_dbg(c):
  # Like android_clang, minus goma, minus static_libarary.
  pass

# GYP_DEFINES must not include 'asan' or 'clang', else the tester bot will try
# to compile clang.
@config_ctx(includes=['chromium_no_goma'])
def chromium_win_asan(c):
  c.runtests.run_asan_test = True

@config_ctx()
def chromium_sanitizer(c):
  c.runtests.test_args.append('--test-launcher-print-test-stdio=always')

@config_ctx(includes=['ninja', 'clang', 'goma', 'asan', 'chromium_sanitizer'])
def chromium_asan(c):
  pass

@config_ctx(includes=['chromium_asan', 'asan_test_batch'])
def chromium_linux_asan(c):
  pass

@config_ctx(includes=['chromium_asan', 'static_library'])
def chromium_mac_asan(c):
  # Need to explicitly set host arch for mac asan 64.
  # TODO(glider, earthdok): Figure out if this is really required or
  # auto-detected by gyp.
  if c.gyp_env.GYP_DEFINES['target_arch'] == 'x64':
    c.gyp_env.GYP_DEFINES['host_arch'] = 'x64'

@config_ctx(includes=['chromium'])
def chromium_mac_mac_views(c):
  c.gyp_env.GYP_DEFINES['mac_views_browser'] = '1'

@config_ctx(includes=['ninja', 'clang', 'goma', 'msan', 'chromium_sanitizer'])
def chromium_msan(c):
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['ninja', 'clang', 'goma', 'syzyasan'])
def chromium_syzyasan(c):  # pragma: no cover
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['ninja', 'clang', 'goma', 'tsan2', 'chromium_sanitizer'])
def chromium_tsan2(c):
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['ninja', 'default_compiler', 'goma', 'chromeos'])
def chromium_chromeos(c):  # pragma: no cover
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['chromium_asan', 'chromiumos', 'asan_test_batch'])
def chromium_chromiumos_asan(c):
  pass

@config_ctx(includes=['ninja', 'clang', 'goma', 'chromeos'])
def chromium_chromeos_clang(c):  # pragma: no cover
  c.compile_py.default_targets = ['all']

@config_ctx(includes=['chromium_chromeos', 'ozone'])
def chromium_chromeos_ozone(c):  # pragma: no cover
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

# TODO(phajdan.jr): cover or remove blink; used by blink_downstream.
@config_ctx(includes=['chromium'])
def blink(c):  # pragma: no cover
  c.compile_py.default_targets = ['blink_tests']

@config_ctx()
def blink_logging_on(c, invert=False):
  c.gyp_env.GYP_DEFINES['blink_logging_always_on'] = int(not invert)

@config_ctx(includes=['android_common', 'ninja', 'static_library',
                      'default_compiler', 'goma'])
def android(c):
  pass

@config_ctx(includes=['android_common', 'ninja', 'static_library', 'clang',
                      'goma'])
def android_clang(c):
  pass

@config_ctx(includes=['android_common', 'ninja', 'shared_library', 'clang',
                      'goma', 'asan'])
def android_asan(c):
  # ASan for Android needs shared_library, so it needs it own config.
  # See https://www.chromium.org/developers/testing/addresssanitizer.
  pass

@config_ctx()
def android_common(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['fastbuild'] = 1
  gyp_defs['OS'] = 'android'

  c.env.PATH.extend([
      c.CHECKOUT_PATH.join(
          'third_party', 'android_tools', 'sdk', 'platform-tools'),
      c.CHECKOUT_PATH.join('build', 'android')])

@config_ctx(includes=['ninja', 'shared_library', 'clang', 'goma'])
def codesearch(c):
  # -k 0 prevents stopping on errors, so the compile step tries to do as much as
  # possible.
  c.compile_py.build_args = ['-k' ,'0']
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['fastbuild'] = 1

@config_ctx(includes=['ninja', 'static_library'])
def chromium_pgo_base(c):
  c.gyp_env.GYP_DEFINES['buildtype'] = 'Official'
  c.gyp_env.GYP_DEFINES['use_goma'] = 0
  fastbuild(c, invert=True)
  c.compile_py.default_targets = ['chrome']

#### 'Full' configurations
@config_ctx(includes=['chromium_pgo_base'])
def chromium_pgo_instrument(c):
  c.gyp_env.GYP_DEFINES['chrome_pgo_phase'] = 1
  # Some of the binaries needed by the PGO gets copied into the build directory
  # during the build, we need to augment the PATH variable so it can find them
  # during the profiling step.
  c.env.PATH.extend([c.build_dir.join(c.build_config_fs)])

@config_ctx(includes=['chromium_pgo_base'])
def chromium_pgo_optimize(c):
  c.gyp_env.GYP_DEFINES['chrome_pgo_phase'] = 2

@config_ctx()
def v8_optimize_medium(c):
  c.gyp_env.GYP_DEFINES['v8_optimized_debug'] = 1

# TODO(phajdan.jr): cover or remove v8_slow_dchecks; used by blink_downstream.
@config_ctx()
def v8_slow_dchecks(c):  # pragma: no cover
  c.gyp_env.GYP_DEFINES['v8_enable_slow_dchecks'] = 1

@config_ctx()
def v8_verify_heap(c):
  c.gyp_env.GYP_DEFINES['v8_enable_verify_heap'] = 1

@config_ctx()
def v8_hybrid_arm(c):
  c.gyp_env.GYP_DEFINES['disable_nacl'] = 1
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = 'arm'
  c.gyp_env.GYP_DEFINES['target_arch'] = 'ia32'
  c.gyp_env.GYP_DEFINES['host_arch'] = 'x86_64'

@config_ctx()
def enable_ipc_fuzzer(c):
  c.gyp_env.GYP_DEFINES['enable_ipc_fuzzer'] = 1

@config_ctx(includes=['chromium_clang'])
def cast_linux(c):
  c.gyp_env.GYP_DEFINES['chromecast'] = 1

@config_ctx()
def internal_gles2_conform_tests(c):
  c.gyp_env.GYP_DEFINES['internal_gles2_conform_tests'] = 1

@config_ctx()
def build_angle_deqp_tests(c):
  c.gyp_env.GYP_DEFINES['build_angle_deqp_tests'] = 1

@config_ctx()
def download_vr_test_apks(c):
  c.gyp_env.DOWNLOAD_VR_TEST_APKS = 1

@config_ctx()
def fetch_telemetry_dependencies(c):
  c.gyp_env.GYP_DEFINES['fetch_telemetry_dependencies'] = 1

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
