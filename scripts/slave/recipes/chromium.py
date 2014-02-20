# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools


DEPS = [
  'archive',
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step_history',
]


class ArchiveBuildStep(object):
  def __init__(self, gs_bucket):
    self.gs_bucket = gs_bucket

  def run(self, api):
    return api.chromium.archive_build(
        'archive build', self.gs_bucket)

  @staticmethod
  def compile_targets():
    return []


class CheckpermsTest(object):
  @staticmethod
  def run(api):
    return api.chromium.checkperms()

  @staticmethod
  def compile_targets():
    return []


class Deps2GitTest(object):
  @staticmethod
  def run(api):
    return api.chromium.deps2git()

  @staticmethod
  def compile_targets():
    return []


class Deps2SubmodulesTest(object):
  @staticmethod
  def run(api):
    return api.chromium.deps2submodules()

  @staticmethod
  def compile_targets():
    return []


class GTestTest(object):
  def __init__(self, name, args=None):
    self.name = name
    self.args = args or []

  def run(self, api):
    return api.chromium.runtest(self.name,
                                args=self.args,
                                annotate='gtest',
                                xvfb=True,
                                parallel=True)

  def compile_targets(self):
    return [self.name]


class TelemetryTest(object):
  def __init__(self, name):
    self.name = name

  def run(self, api):
    return api.chromium.run_telemetry_unittests(self.name)

  @staticmethod
  def compile_targets():
    return ['chrome']


class NaclIntegrationTest(object):
  @staticmethod
  def run(api):
    args = [
      '--mode', api.chromium.c.BUILD_CONFIG,
    ]
    return api.python(
        'nacl_integration',
        api.path.checkout('chrome',
                          'test',
                          'nacl_test_injection',
                          'buildbot_nacl_integration.py'),
        args)

  @staticmethod
  def compile_targets():
    return ['chrome']


# Make it easy to change how different configurations of this recipe
# work without making buildbot-side changes. This contains a dictionary
# of buildbot masters, and each of these dictionaries maps a builder name
# to one of recipe configs below.
BUILDERS = {
  'chromium.chrome': {
    'builders': {
      'Google Chrome ChromeOS': {
        'recipe_config': 'chromeos_official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_targets': [
          'chrome',
          'chrome_sandbox',
          'linux_symbols',
          'symupload'
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Google Chrome Linux': {
        'recipe_config': 'official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'Google Chrome Linux x64': {
        'recipe_config': 'official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'Google Chrome Mac': {
        'recipe_config': 'official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {
          'platform': 'mac',
        },
      },
      'Google Chrome Win': {
        'recipe_config': 'official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {
          'platform': 'win',
        },
      },
    },
  },
  'chromium.chromiumos': {
    'settings': {
      'build_gs_bucket': 'chromium-chromiumos-archive',
    },
    'builders': {
      'Linux ChromiumOS Full': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'compile_targets': [
          'app_list_unittests',
          'aura_builder',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'chromeos_unittests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'message_center_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
        ],
        'tests': [
          ArchiveBuildStep('chromium-browser-snapshots'),
          Deps2GitTest(),
          Deps2SubmodulesTest(),
          CheckpermsTest(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },

      'Linux ChromiumOS Builder': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'app_list_unittests',
          'ash_unittests',
          'aura_builder',
          'aura_unittests',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'chromeos_unittests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'events_unittests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'message_center_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux ChromiumOS Tests (1)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('base_unittests'),
          GTestTest('cacheinvalidation_unittests'),
          GTestTest('chromeos_unittests'),
          GTestTest('components_unittests'),
          GTestTest('crypto_unittests'),
          GTestTest('dbus_unittests'),
          GTestTest('google_apis_unittests'),
          GTestTest('gpu_unittests'),
          GTestTest('url_unittests'),
          GTestTest('jingle_unittests'),
          GTestTest('content_unittests'),
          GTestTest('device_unittests'),
          GTestTest('media_unittests'),
          GTestTest('net_unittests'),
          GTestTest('ppapi_unittests'),
          GTestTest('printing_unittests'),
          GTestTest('remoting_unittests'),
          GTestTest('sandbox_linux_unittests'),
          GTestTest('ui_unittests'),
          GTestTest('views_unittests'),
          GTestTest('aura_unittests'),
          GTestTest('ash_unittests'),
          GTestTest('app_list_unittests'),
          GTestTest('message_center_unittests'),
          GTestTest('compositor_unittests'),
          GTestTest('events_unittests'),
          GTestTest('ipc_tests'),
          GTestTest('sync_unit_tests'),
          GTestTest('unit_tests'),
          GTestTest('sql_unittests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux ChromiumOS Builder',
        },
      },
      'Linux ChromiumOS Tests (2)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('interactive_ui_tests'),
          GTestTest('browser_tests'),
          GTestTest('content_browsertests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux ChromiumOS Builder',
        },
      },

      'Linux ChromiumOS (Clang dbg)': {
        'recipe_config': 'chromium_chromeos_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_targets': [
          'app_list_unittests',
          'aura_builder',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'chromeos_unittests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'message_center_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },

      'Linux ChromiumOS Builder (dbg)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'app_list_unittests',
          'ash_unittests',
          'aura_builder',
          'aura_unittests',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'chromeos_unittests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'events_unittests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'message_center_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux ChromiumOS Tests (dbg)(1)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('base_unittests'),
          GTestTest('cacheinvalidation_unittests'),
          GTestTest('chromeos_unittests'),
          GTestTest('components_unittests'),
          GTestTest('crypto_unittests'),
          GTestTest('dbus_unittests'),
          GTestTest('google_apis_unittests'),
          GTestTest('gpu_unittests'),
          GTestTest('url_unittests'),
          GTestTest('jingle_unittests'),
          GTestTest('content_unittests'),
          GTestTest('device_unittests'),
          GTestTest('media_unittests'),
          GTestTest('net_unittests'),
          GTestTest('ppapi_unittests'),
          GTestTest('printing_unittests'),
          GTestTest('remoting_unittests'),
          GTestTest('sandbox_linux_unittests'),
          GTestTest('ui_unittests'),
          GTestTest('views_unittests'),
          GTestTest('aura_unittests'),
          GTestTest('ash_unittests'),
          GTestTest('app_list_unittests'),
          GTestTest('message_center_unittests'),
          GTestTest('compositor_unittests'),
          GTestTest('events_unittests'),
          GTestTest('ipc_tests'),
          GTestTest('sync_unit_tests'),
          GTestTest('unit_tests'),
          GTestTest('sql_unittests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
        },
      },
      'Linux ChromiumOS Tests (dbg)(2)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('browser_tests'),
          GTestTest('content_browsertests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
        },
      },
      'Linux ChromiumOS Tests (dbg)(3)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('interactive_ui_tests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
        },
      },
    },
  },
  'chromium.linux': {
    'settings': {
      'build_gs_bucket': 'chromium-linux-archive',
    },
    'builders': {
      'Linux Builder': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'app_list_unittests',
          'aura_unittests',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'cast_unittests',
          'cc_unittests',
          'chrome',
          'chromedriver_unittests',
          'chromium_swarm_tests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'events_unittests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_integration_tests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
          'webkit_compositor_bindings_unittests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tests': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('app_list_unittests'),
          GTestTest('aura_unittests'),
          GTestTest('interactive_ui_tests'),
          GTestTest('base_unittests'),
          GTestTest('cacheinvalidation_unittests'),
          GTestTest('cast_unittests'),
          GTestTest('cc_unittests'),
          GTestTest('chromedriver_unittests'),
          GTestTest('components_unittests'),
          GTestTest('compositor_unittests'),
          GTestTest('crypto_unittests'),
          GTestTest('dbus_unittests'),
          GTestTest('google_apis_unittests'),
          GTestTest('gpu_unittests'),
          GTestTest('url_unittests'),
          GTestTest('jingle_unittests'),
          GTestTest('content_unittests'),
          GTestTest('device_unittests'),
          GTestTest('events_unittests'),
          GTestTest('media_unittests'),
          GTestTest('net_unittests'),
          GTestTest('ppapi_unittests'),
          GTestTest('printing_unittests'),
          GTestTest('remoting_unittests'),
          GTestTest('sandbox_linux_unittests'),
          TelemetryTest('telemetry_unittests'),
          TelemetryTest('telemetry_perf_unittests'),
          GTestTest('ui_unittests'),
          GTestTest('ipc_tests'),
          GTestTest('sync_unit_tests'),
          GTestTest('unit_tests'),
          GTestTest('views_unittests'),
          GTestTest('sql_unittests'),
          GTestTest('browser_tests'),
          GTestTest('content_browsertests'),
          GTestTest('webkit_compositor_bindings_unittests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux Builder',
        },
      },
      'Linux Sync': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('sync_integration_tests', args=[
              '--ui-test-action-max-timeout=120000'
          ]),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux Builder',
        },
      },

      'Linux GTK Builder': {
        'recipe_config': 'chromium_gtk',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'cast_unittests',
          'cc_unittests',
          'chrome',
          'chromedriver_unittests',
          'chromium_swarm_tests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_integration_tests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'webkit_compositor_bindings_unittests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux GTK Tests': {
        'recipe_config': 'chromium_gtk',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('interactive_ui_tests'),
          GTestTest('base_unittests'),
          GTestTest('cacheinvalidation_unittests'),
          GTestTest('cast_unittests'),
          GTestTest('cc_unittests'),
          GTestTest('chromedriver_unittests'),
          GTestTest('components_unittests'),
          GTestTest('crypto_unittests'),
          GTestTest('dbus_unittests'),
          GTestTest('google_apis_unittests'),
          GTestTest('gpu_unittests'),
          GTestTest('url_unittests'),
          GTestTest('jingle_unittests'),
          GTestTest('content_unittests'),
          GTestTest('device_unittests'),
          GTestTest('media_unittests'),
          GTestTest('net_unittests'),
          GTestTest('ppapi_unittests'),
          GTestTest('printing_unittests'),
          GTestTest('remoting_unittests'),
          GTestTest('sandbox_linux_unittests'),
          GTestTest('ui_unittests'),
          GTestTest('ipc_tests'),
          GTestTest('sync_unit_tests'),
          GTestTest('unit_tests'),
          GTestTest('sql_unittests'),
          GTestTest('browser_tests'),
          GTestTest('content_browsertests'),
          GTestTest('webkit_compositor_bindings_unittests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux GTK Builder',
        },
      },

      'Linux Builder (dbg)(32)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'app_list_unittests',
          'aura_unittests',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'cast_unittests',
          'cc_unittests',
          'chrome',
          'chromedriver_unittests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'events_unittests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_integration_tests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
          'webkit_compositor_bindings_unittests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tests (dbg)(1)(32)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('net_unittests'),
          GTestTest('browser_tests'),
          GTestTest('content_browsertests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux Builder (dbg)(32)',
        },
      },
      'Linux Tests (dbg)(2)(32)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('app_list_unittests'),
          GTestTest('aura_unittests'),
          GTestTest('interactive_ui_tests'),
          GTestTest('base_unittests'),
          GTestTest('cacheinvalidation_unittests'),
          GTestTest('cast_unittests'),
          GTestTest('cc_unittests'),
          GTestTest('chromedriver_unittests'),
          GTestTest('components_unittests'),
          GTestTest('compositor_unittests'),
          GTestTest('crypto_unittests'),
          GTestTest('dbus_unittests'),
          GTestTest('gpu_unittests'),
          GTestTest('url_unittests'),
          GTestTest('jingle_unittests'),
          GTestTest('content_unittests'),
          GTestTest('device_unittests'),
          GTestTest('events_unittests'),
          GTestTest('media_unittests'),
          GTestTest('ppapi_unittests'),
          GTestTest('printing_unittests'),
          GTestTest('remoting_unittests'),
          GTestTest('sandbox_linux_unittests'),
          GTestTest('ui_unittests'),
          GTestTest('ipc_tests'),
          GTestTest('sync_unit_tests'),
          GTestTest('unit_tests'),
          GTestTest('views_unittests'),
          GTestTest('sql_unittests'),
          GTestTest('webkit_compositor_bindings_unittests'),
          NaclIntegrationTest(),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux Builder (dbg)(32)',
        },
      },

      'Linux Builder (dbg)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'app_list_unittests',
          'aura_unittests',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'cast_unittests',
          'cc_unittests',
          'chrome',
          'chromedriver_unittests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'events_unittests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
          'webkit_compositor_bindings_unittests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tests (dbg)(1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('net_unittests'),
          GTestTest('browser_tests'),
          GTestTest('content_browsertests'),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux Builder (dbg)',
        },
      },
      'Linux Tests (dbg)(2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('app_list_unittests'),
          GTestTest('aura_unittests'),
          GTestTest('interactive_ui_tests'),
          GTestTest('base_unittests'),
          GTestTest('cacheinvalidation_unittests'),
          GTestTest('cast_unittests'),
          GTestTest('cc_unittests'),
          GTestTest('chromedriver_unittests'),
          GTestTest('components_unittests'),
          GTestTest('compositor_unittests'),
          GTestTest('crypto_unittests'),
          GTestTest('dbus_unittests'),
          GTestTest('google_apis_unittests'),
          GTestTest('gpu_unittests'),
          GTestTest('url_unittests'),
          GTestTest('jingle_unittests'),
          GTestTest('content_unittests'),
          GTestTest('device_unittests'),
          GTestTest('events_unittests'),
          GTestTest('media_unittests'),
          GTestTest('ppapi_unittests'),
          GTestTest('printing_unittests'),
          GTestTest('remoting_unittests'),
          GTestTest('sandbox_linux_unittests'),
          GTestTest('ui_unittests'),
          GTestTest('ipc_tests'),
          GTestTest('sync_unit_tests'),
          GTestTest('unit_tests'),
          GTestTest('views_unittests'),
          GTestTest('sql_unittests'),
          GTestTest('webkit_compositor_bindings_unittests'),
          NaclIntegrationTest(),
        ],
        'testing': {
          'platform': 'linux',
          'parent_buildername': 'Linux Builder (dbg)',
        },
      },

      'Linux Clang (dbg)': {
        'recipe_config': 'chromium_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_targets': [
          'all',
          'base_unittests',
          'components_unittests',
          'crypto_unittests',
          'google_apis_unittests',
          'content_unittests',
          'device_unittests',
          'sandbox_linux_unittests',
          'ui_unittests',
          'ipc_tests',
          'sync_unit_tests',
          'unit_tests',
          'sql_unittests',
        ],
        'tests': [
          GTestTest('base_unittests'),
          GTestTest('components_unittests'),
          GTestTest('crypto_unittests'),
          GTestTest('google_apis_unittests'),
          GTestTest('content_unittests'),
          GTestTest('device_unittests'),
          GTestTest('sandbox_linux_unittests'),
          GTestTest('ui_unittests'),
          GTestTest('ipc_tests'),
          GTestTest('sync_unit_tests'),
          GTestTest('unit_tests'),
          GTestTest('sql_unittests'),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
}


# Different types of builds this recipe can do.
RECIPE_CONFIGS = {
  'chromeos_official': {
    'chromium_config': 'chromium_official',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'chromium': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
  },
  'chromium_clang': {
    'chromium_config': 'chromium_clang',
    'gclient_config': 'chromium',
  },
  'chromium_gtk': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['gtk'],
    'gclient_config': 'chromium',
  },
  'chromium_chromeos': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chromium_chromeos_clang': {
    'chromium_config': 'chromium_clang',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'official': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  master_config = master_dict.get('settings', {})
  recipe_config_name = bot_config['recipe_config']
  assert recipe_config_name, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.chromium.set_config(recipe_config['chromium_config'],
                          **bot_config.get('chromium_config_kwargs', {}))
  for c in recipe_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  api.gclient.set_config(recipe_config['gclient_config'])
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  # For non-trybot recipes we should know (seed) all steps in advance,
  # at the beginning of each build. Instead of yielding single steps
  # or groups of steps, yield all of them at the end.
  steps = [
    api.gclient.checkout(),
    api.chromium.runhooks(),
    api.chromium.cleanup_temp(),
  ]

  bot_type = bot_config.get('bot_type', 'builder_tester')

  if bot_type in ['builder', 'builder_tester']:
    steps.extend([
        api.chromium.compile(targets=bot_config.get('compile_targets')),
        api.chromium.checkdeps(),
    ])

  if bot_type == 'builder':
    steps.append(api.archive.zip_and_upload_build(
        'package build',
        api.chromium.c.build_config_fs,
        api.archive.legacy_upload_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=api.properties['mastername'])))

  if bot_type == 'tester':
    # Protect against hard to debug mismatches between directory names
    # used to run tests from and extract build to. We've had several cases
    # where a stale build directory was used on a tester, and the extracted
    # build was not used at all, leading to confusion why source code changes
    # are not taking effect.
    #
    # The best way to ensure the old build directory is not used is to
    # remove it.
    steps.append(api.path.rmtree(
      'build directory',
      api.chromium.c.build_dir(api.chromium.c.build_config_fs)))

    steps.append(api.archive.download_and_unzip_build(
      'extract build',
      api.chromium.c.build_config_fs,
      api.archive.legacy_download_url(
        master_config.get('build_gs_bucket'),
        extra_url_components=api.properties['mastername']),
      # TODO(phajdan.jr): Move abort_on_failure to archive recipe module.
      abort_on_failure=True))

  if bot_type in ['tester', 'builder_tester']:
    steps.extend([t.run(api) for t in bot_config.get('tests', [])])

  # For non-trybot recipes we should know (seed) all steps in advance,
  # at the beginning of each build. Instead of yielding single steps
  # or groups of steps, yield all of them at the end.
  yield steps


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config['testing'].get('parent_buildername') is None, (
            'Unexpected parent_buildername for builder %r on master %r.' %
                (buildername, mastername))

      # Verify that required targets are in fact compiled. This is a common
      # class of errors (mismatch of what is compiled on builder and required
      # on tester), and preventing it at recipe writing/testing time is a big
      # win for stability of production infrastructure.
      if bot_type in ['tester', 'builder_tester']:
        required_targets = set(itertools.chain(
            *[t.compile_targets() for t in bot_config.get('tests', [])]))

        if bot_type == 'tester':
          parent_buildername = bot_config['testing']['parent_buildername']
          compile_config = master_config['builders'][parent_buildername]
          compiled_targets = set(compile_config['compile_targets'])
        elif bot_type == 'builder_tester':
          parent_buildername = buildername
          compiled_targets = set(bot_config.get('compile_targets', []))

        assert required_targets.issubset(compiled_targets), (
            'On master "%s" builder "%s" requires the following targets to be '
            'compiled on builder "%s": %s' % (
                mastername,
                buildername,
                parent_buildername,
                ', '.join(required_targets - compiled_targets)))

      test = (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties(mastername=mastername,
                       buildername=buildername,
                       parent_buildername=bot_config['testing'].get(
                           'parent_buildername')) +
        api.platform(bot_config['testing']['platform'],
                     bot_config.get(
                         'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
      )

      if bot_type in ['builder', 'builder_tester']:
        test += api.step_data('checkdeps', api.json.output([]))

      yield test
