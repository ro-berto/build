# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from recipe_engine import recipe_api
from recipe_engine.types import freeze
from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

DEPS = [
  'chromium',
  'chromium_android',
  'chromium_tests',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/buildbucket',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'depot_tools/tryserver',
]

BUILDERS = freeze({
  'chromium.perf': {
    'Android Builder Perf': {
      'recipe_config': 'main_builder_rel_mb',
      'gclient_apply_config': ['android', 'perf'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload_for_bisect': {
        'bucket': 'chrome-test-builds',
        'path': lambda api: (
            'official-by-commit/Android Builder/full-build-linux_%s.zip'),
      },
      'upload': {
        'bucket': 'chrome-perf',
        'path': lambda api: ('Android Builder/full-build-linux_%s.zip'
                             % api.buildbucket.gitiles_commit.id),
      },
      'resource_sizes_apks': [
        'ChromeModernPublic.minimal.apks',
        'ChromePublic.apk',
        'MonochromePublic.minimal.apks',
        'SystemWebView.apk',
      ],
      'run_mb': True,
      'targets': [
        'android_tools',
        'chrome_modern_public_minimal_apks',
        'chrome_public_apk',
        'dump_syms',
        'microdump_stackwalk',
        'monochrome_public_minimal_apks',
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
      ],
    },
    'Android arm64 Builder Perf': {
      'recipe_config': 'arm64_builder_rel_mb',
      'gclient_apply_config': ['android', 'perf'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload_for_bisect': {
        'bucket': 'chrome-test-builds',
        'path': lambda api: (
            'official-by-commit/Android arm64 Builder/full-build-linux_%s.zip'),
      },
      'upload': {
        'bucket': 'chrome-perf',
        'path': lambda api: (
            'Android arm64 Builder/full-build-linux_%s.zip'
            % api.buildbucket.gitiles_commit.id),
      },
      'resource_sizes_apks': [
        'ChromeModernPublic.minimal.apks',
        'ChromePublic.apk',
        'SystemWebView.apk',
      ],
      'run_mb': True,
      'targets': [
        'android_tools',
        'chrome_modern_public_minimal_apks',
        'chrome_public_apk',
        'dump_syms',
        'microdump_stackwalk',

        # 64-bit Monochrome builds 32-bit libchrome.so as well, so do not add it
        # here unless it's beneficial and doesn't slow the bots down too much.
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
      ],
    }
  },
  'client.v8.fyi': {
    'Android Builder': {
      'recipe_config': 'main_builder_rel_mb',
      'gclient_apply_config': [
        'android',
        'perf',
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'v8-android',
        'path': lambda api: ('v8_android_perf_rel/full-build-linux_%s.zip'
                             % api.buildbucket.gitiles_commit.id),
      },
      'run_mb': True,
      'targets': [
        'android_tools',
        'cc_perftests',
        'chrome_public_apk',
        'gpu_perftests',
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
    }
  },
})

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'mastername': Property(),
  'buildername': Property(),
  'revision': Property(default='HEAD'),
}

def _GetChromiumTestsCompileTargets(api, mastername, buildername, update_step):
  # This is a bridge to the chromium recipe for the perf bots, allowing us to
  # solely use src/-side test specifications before switching.
  ct_bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)])
  ct_bot_db = api.chromium_tests.create_bot_db_object()
  ct_bot_config.initialize_bot_db(api.chromium_tests, ct_bot_db, update_step)
  test_config = api.chromium_tests.get_tests(ct_bot_config, ct_bot_db)
  return api.chromium_tests.get_compile_targets(
      ct_bot_config, ct_bot_db, test_config.all_tests())

def _RunStepsInternal(api, mastername, buildername, revision):
  bot_config = BUILDERS[mastername][buildername]
  droid = api.chromium_android

  default_kwargs = {
    'REPO_URL': 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src',
    'INTERNAL': False,
    'REPO_NAME': 'src',
    'BUILD_CONFIG': bot_config.get('target', 'Debug'),
  }
  default_kwargs.update(bot_config.get('kwargs', {}))
  droid.configure_from_properties(bot_config['recipe_config'], **default_kwargs)
  api.chromium.set_config(bot_config['recipe_config'], **default_kwargs)
  api.chromium_tests.set_config('chromium')
  droid.c.set_val({'deps_file': 'DEPS'})

  api.gclient.set_config('chromium')
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if bot_config.get('set_component_rev'):
    # If this is a component build and the main revision is e.g. blink,
    # webrtc, or v8, the custom deps revision of this component must be
    # dynamically set to either:
    # (1) 'revision' from the waterfall, or
    # (2) 'HEAD' for forced builds with unspecified 'revision'.
    component_rev = revision
    dep = bot_config.get('set_component_rev')
    api.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev

  api.chromium.ensure_goma()
  update_step = api.bot_update.ensure_checkout()
  api.chromium_android.clean_local_files()

  api.chromium.runhooks()

  if bot_config.get('run_mb'):
    _, raw_result = api.chromium.mb_gen(
        mastername, buildername, use_goma=True)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result

  targets = list(bot_config.get('targets', []))
  targets += _GetChromiumTestsCompileTargets(
      api, mastername, buildername, update_step)
  raw_result = api.chromium.compile(targets, use_goma_module=True)
  if raw_result.status != common_pb.SUCCESS:
    return raw_result

  for apk_name in bot_config.get('resource_sizes_apks', ()):
    apk_path = api.chromium_android.apk_path(apk_name)
    size_path = api.chromium_android.apk_path(apk_name + '.size')
    api.chromium_android.resource_sizes(apk_path, chartjson_file=True)
    api.chromium_android.supersize_archive(apk_path, size_path)

  upload_for_bisect = bot_config.get('upload_for_bisect')
  if upload_for_bisect:
    droid.upload_apks_for_bisect(update_step.presentation.properties,
                                 upload_for_bisect['bucket'],
                                 upload_for_bisect['path'](api))

  upload_config = bot_config.get('upload')
  if upload_config:
    droid.upload_build(upload_config['bucket'],
                       upload_config['path'](api))


def RunSteps(api, mastername, buildername, revision):
  return _RunStepsInternal(api, mastername, buildername, revision)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  # tests bots in BUILDERS
  for mastername, builders in BUILDERS.iteritems():
    for buildername in builders:
      yield (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(buildername=buildername,
            repository='svn://svn.chromium.org/chrome/trunk/src',
            buildnumber=257,
            mastername=mastername,
            issue='8675309',
            patchset='1',
            revision='a' * 40,
            got_revision='a' * 40))

  yield(
    api.test('compile_failure') +
    api.properties.generic(
        mastername='chromium.perf',
        repository='svn://svn.chromium.org/chrome/trunk/src',
        buildnumber=257,
        buildername='Android Builder Perf',
        issue='8675309',
        patchset='1',
        revision='a' * 40,
        got_revision='a' * 40) +
    api.step_data('compile', retcode=1) +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('mb_gen_failure') +
    api.properties.generic(buildername='Android Builder Perf',
        repository='svn://svn.chromium.org/chrome/trunk/src',
        buildnumber=257,
        mastername='chromium.perf',
        issue='8675309',
        patchset='1',
        revision='a' * 40,
        got_revision='a' * 40) +
    api.step_data('generate_build_files', retcode=1) +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )
