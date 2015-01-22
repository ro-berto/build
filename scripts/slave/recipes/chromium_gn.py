# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze

DEPS = [
  'bot_update',
  'chromium',
  'platform',
  'properties',
]


BUILDERS = freeze({
  'chromium.mac': {
    'builders': {
      'Mac GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
        },
      },
      'Mac GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'mac',
        },
      },
    },
  },
  'chromium.webkit': {
    'builders': {
      'Android GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android', 'blink'],
      },
      'Android GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android', 'blink'],
      },
      'Linux GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'gclient_apply_config': ['blink'],
        'should_run_mojo_tests': True,
      },
      'Linux GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['gn_component_build'],
        'gclient_apply_config': ['blink'],
      },
    },
  },
  'tryserver.blink': {
    'builders': {
      'android_chromium_gn_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android', 'blink'],
      },
      'linux_chromium_gn_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'gclient_apply_config': ['blink'],
      },
    },
  },
  'chromium.chromiumos': {
    'builders': {
      'Linux ChromiumOS GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'chromeos',
        },
      },
    },
  },
  'chromium.linux': {
    'builders': {
      'Android GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'Android GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'Linux GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'should_run_gn_gyp_compare': True,
      },
      'Linux GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['gn_component_build'],
        'should_run_gn_gyp_compare': True,
      },
    },
  },
  'chromium.win': {
    'builders': {
      'Win8 GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
      },
     'Win8 GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
      },
    },
  },
  'tryserver.chromium.linux': {
    'builders': {
      'android_chromium_gn_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'android_chromium_gn_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'linux_chromium_gn_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'should_run_mojo_tests': True,
      },
      'linux_chromium_gn_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['gn_component_build'],
      },
      'linux_chromium_gn_chromeos_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'chromeos',
        },
      },
      'linux_chromium_gn_chromeos_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'chromeos',
        },
        'chromium_apply_config': ['gn_component_build'],
      },
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
      'mac_chromium_gn_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'mac',
        },
      },
      'mac_chromium_gn_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
        },
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win8_chromium_gn_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
      },
      'win8_chromium_gn_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
      },
    }
  },
  'tryserver.v8': {
    'builders': {
      'v8_linux_chromium_gn_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'gclient_apply_config': [
          'v8_bleeding_edge_git',
          'chromium_lkcr',
          'show_v8_revision',
        ],
        'root_override': 'src/v8',
        'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      },
      'v8_android_chromium_gn_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': [
          'android',
          'v8_bleeding_edge_git',
          'chromium_lkcr',
          'show_v8_revision',
        ],
        'root_override': 'src/v8',
        'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      },
    },
  },
  'client.v8': {
    'builders': {
      'V8 Linux GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'gclient_apply_config': [
          'v8_bleeding_edge_git',
          'chromium_lkcr',
          'show_v8_revision',
        ],
        'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      },
      'V8 Android GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': [
          'android',
          'v8_bleeding_edge_git',
          'chromium_lkcr',
          'show_v8_revision',
        ],
        'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      },
    },
  },
})

def GenSteps(api):
  buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['gn'])

  api.bot_update.ensure_checkout(
      force=True, patch_root=bot_config.get('root_override'))

  api.chromium.runhooks()

  # TODO(dpranke): goma doesn't work on windows GN builds yet.
  is_windows = ('Win' in buildername or 'win' in buildername)
  api.chromium.run_gn(use_goma=not is_windows)
  if is_windows:
    api.chromium.c.compile_py.compiler = None
    api.chromium.c.compile_py.goma_dir = None

  api.chromium.compile(targets=['all'])

  # TODO(dpranke): Ensure that every bot runs w/ --check, then make
  # it be on by default.
  if bot_config.get('should_run_gn_check', True):
      api.chromium.run_gn_check()

  if bot_config.get('should_run_gn_gyp_compare', False):
    api.chromium.run_gn_compare()

  # TODO(dpranke): crbug.com/353854. Run gn_unittests and other tests
  # when they are also being run as part of the try jobs.
  if bot_config.get('should_run_mojo_tests', False):
    api.chromium.runtest('html_viewer_unittests')


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

  yield (
    api.test('compile_failure') +
    api.platform.name('linux') +
    api.properties.tryserver(
        buildername='linux_chromium_gn_rel',
        mastername='tryserver.chromium.linux') +
    api.step_data('compile', retcode=1)
  )
