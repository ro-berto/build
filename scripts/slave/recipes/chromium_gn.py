# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze

DEPS = [
  'bot_update',
  'chromium',
  'chromium_tests',
  'json',
  'path',
  'platform',
  'properties',
  'tryserver',
]


BUILDERS = freeze({
  'chromium.mac': {
    'builders': {
      'Mac GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
        },
        'should_use_mb': True,
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
        'chromium_apply_config': ['gn_minimal_symbols'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android', 'blink'],
      },
      'Android GN (dbg)': {
        'chromium_apply_config': ['gn_minimal_symbols'],
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
        'chromium_apply_config': ['gn_component_build'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'gclient_apply_config': ['blink'],
      },
    },
  },
  'tryserver.blink': {
    'builders': {
      'android_chromium_gn_compile_rel': {
        'chromium_apply_config': ['gn_minimal_symbols'],
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
        'chromium_apply_config': ['gn_minimal_symbols'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'Android GN (dbg)': {
        'chromium_apply_config': ['gn_minimal_symbols'],
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
        'chromium_apply_config': ['gn_component_build'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'should_run_gn_gyp_compare': True,
      },
    },
  },
  'chromium.win': {
    'builders': {
      'Win8 GN': {
        'chromium_apply_config': ['gn_minimal_symbols'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
        'should_use_mb': True,
      },
     'Win8 GN (dbg)': {
        'chromium_apply_config': ['gn_minimal_symbols'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
        'should_use_mb': True,
      },
    },
  },
  'tryserver.chromium.linux': {
    'builders': {
      'android_chromium_gn_compile_rel': {
        'chromium_apply_config': ['gn_minimal_symbols'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'android_chromium_gn_compile_dbg': {
        'chromium_apply_config': ['gn_minimal_symbols'],
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
      },
      'linux_chromium_gn_dbg': {
        'chromium_apply_config': ['gn_component_build'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
      },
      'linux_chromium_gn_chromeos_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'chromeos',
        },
      },
      'linux_chromium_gn_chromeos_dbg': {
        'chromium_apply_config': ['gn_component_build'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'chromeos',
        },
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
        'should_use_mb': True,
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win8_chromium_gn_dbg': {
        'chromium_apply_config': ['gn_minimal_symbols'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
        'should_use_mb': True,
      },
      'win8_chromium_gn_rel': {
        'chromium_apply_config': ['gn_minimal_symbols'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
        'should_use_mb': True,
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
        'chromium_apply_config': ['gn_minimal_symbols'],
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
        'chromium_apply_config': ['gn_minimal_symbols'],
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

def all_compile_targets(api, tests):
  """Returns the compile_targets for all the Tests in |tests|."""
  return sorted(set(x
                    for test in tests
                    for x in test.compile_targets(api)))


def _GenStepsInternal(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  bot_config = BUILDERS[mastername]['builders'][buildername]
  should_use_mb = bot_config.get('should_use_mb', False)
  is_android = ('Android' in buildername or 'android' in buildername)

  if should_use_mb:
    api.chromium.configure_bot(BUILDERS, ['gn'])
    api.bot_update.ensure_checkout(
       force=True, patch_root=bot_config.get('root_override'))

    # because the 'gn' config is applied, we skip running gyp in the
    # the runhooks step.
    api.chromium.runhooks()

    api.chromium.run_mb(mastername, buildername, use_goma=True)

    # TODO(dpranke): Unify this with the logic in the chromium_trybot and
    # chromium recipes so that we can actually run the tests as well
    # and deapply patches and retry as need be.
    test_spec_file = '%s.json' % mastername
    test_spec = api.chromium_tests.read_test_spec(api, test_spec_file)
    tests = list(api.chromium.steps.generate_gtest(api, mastername,
                                                   buildername, test_spec))
    additional_compile_targets = test_spec.get(buildername, {}).get(
        'additional_compile_targets',
        ['chrome_shell_apk' if is_android else 'all'])

    if api.tryserver.is_tryserver:
      affected_files = api.tryserver.get_files_affected_by_patch()

      test_compile_targets = all_compile_targets(api, tests)

      requires_compile, _, compile_targets = \
          api.chromium_tests.analyze(
              affected_files,
              test_compile_targets + additional_compile_targets,
              test_compile_targets,
              'trybot_analyze_config.json',
              use_mb=True,
              build_output_dir='//out/%s' % api.chromium.c.build_config_fs)
      if requires_compile:
        api.chromium.compile(compile_targets)
    else:
      api.chromium.compile(all_compile_targets(api, tests) +
                           additional_compile_targets)
  else:
    api.chromium.configure_bot(BUILDERS, ['gn'])
    api.bot_update.ensure_checkout(
       force=True, patch_root=bot_config.get('root_override'))
    api.chromium.runhooks()
    api.chromium.run_gn(use_goma=True)

    # crbug.com/451227 - building 'all' on android builds too many
    # things. Really we should be building the 'default' target
    # on all platforms but that isn't properly defined yet.
    if is_android:
      targets = ['chrome_shell_apk']
    else:
      targets = ['all']
    api.chromium.compile(targets)

  # TODO(dpranke): Ensure that every bot runs w/ --check, then make
  # it be on by default.
  if bot_config.get('should_run_gn_check', True):
    api.chromium.run_gn_check()

  if bot_config.get('should_run_gn_gyp_compare', False):
    api.chromium.run_gn_compare()

  if not is_android and not should_use_mb:
    api.chromium.runtest('gn_unittests')


def GenSteps(api):
  with api.tryserver.set_failure_hash():
    return _GenStepsInternal(api)


def GenTests(api):
  overrides = {}
  for mastername, master_dict in BUILDERS.items():
    for buildername, builder_dict in master_dict['builders'].items():
      if builder_dict.get('should_use_mb', False):
        overrides.setdefault(mastername, {})
        overrides[mastername][buildername] = (
           api.override_step_data(
               'read test spec',
               api.json.output({
                   buildername: {
                     'gtest_tests': ['base_unittests'],
                   },
               })))

        if 'tryserver' in mastername:
           overrides[mastername][buildername] += api.override_step_data(
              'analyze',
              api.json.output({
                  'status': 'Found dependency',
                  'targets': ['base_unittests'],
                  'build_targets': ['base_unittests'],
              }))

  for test in api.chromium.gen_tests_for_builders(BUILDERS, overrides):
    yield test

  yield (
    api.test('compile_failure') +
    api.platform.name('linux') +
    api.properties.tryserver(
        buildername='linux_chromium_gn_rel',
        mastername='tryserver.chromium.linux') +
    api.step_data('compile', retcode=1)
  )

  yield (
    api.test('use_v8_patch_on_chromium_gn_trybot') +
    api.platform.name('linux') +
    api.properties.tryserver(
        buildername='linux_chromium_gn_rel',
        mastername='tryserver.chromium.linux',
        patch_project='v8')
  )
