# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'build',
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'goma',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

def build_with_goma_module(api):
  # chromedriver compile with goma module step
  build_target_dir = str(api.path["checkout"].join("out", "Default"))
  api.goma.build_with_goma(
      name='compile',
      ninja_command=[str(api.depot_tools.ninja_path),
                     '-C', build_target_dir,
                     '-j', api.goma.recommended_goma_jobs,
                     'chromedriver',
                     'chromedriver_tests',
                     'chromedriver_unittests'],
      ninja_log_outdir=build_target_dir,
      ninja_log_compiler='goma')


def Linux32_steps(api):
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "src"
  soln.url = "https://chromium.googlesource.com/chromium/src.git"
  soln.custom_deps = {'src/chrome/test/chromedriver/third_party/java_tests':
      'https://chromium.googlesource.com/chromium/deps/webdriver'}
  soln = src_cfg.solutions.add()
  soln.name = "src-internal"
  soln.url = "https://chrome-internal.googlesource.com/chrome/src-internal.git"
  soln.custom_deps = {'src/chrome/test/data/firefox2_searchplugins': None,
      'src/tools/grit/grit/test/data': None,
      'src/chrome/test/data/firefox3_searchplugins': None,
      'src/webkit/data/test_shell/plugins': None,
      'src/data/page_cycler': None,
      'src/data/mozilla_js_tests': None,
      'src/chrome/test/data/firefox2_profile/searchplugins': None,
      'src/data/esctf': None,
      'src/data/memory_test': None,
      'src/data/mach_ports': None,
      'src/webkit/data/xbm_decoder': None,
      'src/webkit/data/ico_decoder': None,
      'src/data/selenium_core': None,
      'src/chrome/test/data/ssl/certs': None,
      'src/chrome/test/data/osdd': None,
      'src/webkit/data/bmp_decoder': None,
      'src/chrome/test/data/firefox3_profile/searchplugins': None,
      'src/data/autodiscovery': None}
  src_cfg.got_revision_mapping.update({'src': 'got_revision',
    'src/third_party/WebKit': 'got_webkit_revision',
    'src/tools/swarming_client': 'got_swarming_client_revision',
    'src/v8': 'got_v8_revision'})
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout()
  build_properties = api.properties.legacy()
  build_properties.update(result.json.output.get('properties', {}))
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {'LANDMINES_VERBOSE': '1', 'DEPOT_TOOLS_UPDATE': '0'}
  with api.context(env=env):
    api.build.python("gclient runhooks wrapper",
        api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"))
  # meta build step
  goma_dir = api.goma.ensure_goma()
  api.python("meta build", api.path["checkout"].join("tools", "mb", "mb.py"),
      args=["gen", "-m", "chromium.chromedriver", "-b",
          build_properties.get('buildername'), "--goma-dir", goma_dir,
          "//out/Default"])

  build_with_goma_module(api)

  # strip binary
  api.m.step('strip', cmd=['strip', str(api.path['checkout'].join(
      'out', 'Default', 'chromedriver'))])

  # annotated_steps step
  annotated_steps(api, build_properties.get('got_revision'))


def Mac_10_6_steps(api):
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "src"
  soln.url = "https://chromium.googlesource.com/chromium/src.git"
  soln.custom_deps = {'src/chrome/test/chromedriver/third_party/java_tests':
      'https://chromium.googlesource.com/chromium/deps/webdriver'}
  soln = src_cfg.solutions.add()
  soln.name = "src-internal"
  soln.url = "https://chrome-internal.googlesource.com/chrome/src-internal.git"
  soln.custom_deps = {'src/chrome/test/data/firefox2_searchplugins': None,
      'src/tools/grit/grit/test/data': None,
      'src/chrome/test/data/firefox3_searchplugins': None,
      'src/webkit/data/test_shell/plugins': None,
      'src/data/page_cycler': None,
      'src/data/mozilla_js_tests': None,
      'src/chrome/test/data/firefox2_profile/searchplugins': None,
      'src/data/esctf': None,
      'src/data/memory_test': None,
      'src/data/mach_ports': None,
      'src/webkit/data/xbm_decoder': None,
      'src/webkit/data/ico_decoder': None,
      'src/data/selenium_core': None,
      'src/chrome/test/data/ssl/certs': None,
      'src/chrome/test/data/osdd': None,
      'src/webkit/data/bmp_decoder': None,
      'src/chrome/test/data/firefox3_profile/searchplugins': None,
      'src/data/autodiscovery': None}
  src_cfg.got_revision_mapping.update({'src': 'got_revision',
    'src/third_party/WebKit': 'got_webkit_revision',
    'src/tools/swarming_client': 'got_swarming_client_revision',
    'src/v8': 'got_v8_revision'})
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout()
  build_properties = api.properties.legacy()
  build_properties.update(result.json.output.get('properties', {}))
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {'LANDMINES_VERBOSE': '1', 'DEPOT_TOOLS_UPDATE': '0'}
  with api.context(env=env):
    api.build.python("gclient runhooks wrapper",
        api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"))
  # meta build step
  goma_dir = api.goma.ensure_goma()
  api.python("meta build", api.path["checkout"].join("tools", "mb", "mb.py"),
      args=["gen", "-m", "chromium.chromedriver", "-b",
          build_properties.get('buildername'), "--goma-dir", goma_dir,
          "//out/Default"])

  build_with_goma_module(api)

  # strip binary
  api.m.step('strip', cmd=['strip', str(api.path['checkout'].join(
      'out', 'Default', 'chromedriver'))])

  # annotated_steps step
  annotated_steps(api, build_properties.get('got_revision'))


def Win7_steps(api):
  # update scripts step; implicitly run by recipe engine.
  # taskkill step
  api.build.python("taskkill", api.package_repo_resource("scripts", "slave",
    "kill_processes.py"))
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "src"
  soln.url = "https://chromium.googlesource.com/chromium/src.git"
  soln.custom_deps = {'src/chrome/test/chromedriver/third_party/java_tests':
      'https://chromium.googlesource.com/chromium/deps/webdriver'}
  soln = src_cfg.solutions.add()
  soln.name = "src-internal"
  soln.url = "https://chrome-internal.googlesource.com/chrome/src-internal.git"
  soln.custom_deps = {'src/chrome/test/data/firefox2_searchplugins': None,
      'src/tools/grit/grit/test/data': None,
      'src/chrome/test/data/firefox3_searchplugins': None,
      'src/webkit/data/test_shell/plugins': None,
      'src/data/page_cycler': None,
      'src/data/mozilla_js_tests': None,
      'src/chrome/test/data/firefox2_profile/searchplugins': None,
      'src/data/esctf': None,
      'src/data/memory_test': None,
      'src/data/mach_ports': None,
      'src/webkit/data/xbm_decoder': None,
      'src/webkit/data/ico_decoder': None,
      'src/data/selenium_core': None,
      'src/chrome/test/data/ssl/certs': None,
      'src/chrome/test/data/osdd': None,
      'src/webkit/data/bmp_decoder': None,
      'src/chrome/test/data/firefox3_profile/searchplugins': None,
      'src/data/autodiscovery': None}
  src_cfg.got_revision_mapping.update({'src': 'got_revision',
    'src/third_party/WebKit': 'got_webkit_revision',
    'src/tools/swarming_client': 'got_swarming_client_revision',
    'src/v8': 'got_v8_revision'})
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout()
  build_properties = api.properties.legacy()
  build_properties.update(result.json.output.get('properties', {}))
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {'LANDMINES_VERBOSE': '1', 'DEPOT_TOOLS_UPDATE': '0'}
  with api.context(env=env):
    api.build.python("gclient runhooks wrapper",
        api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"))
  # meta build step
  goma_dir = api.goma.ensure_goma()
  api.python("meta build", api.path["checkout"].join("tools", "mb", "mb.py"),
      args=["gen", "-m", "chromium.chromedriver", "-b",
          build_properties.get('buildername'), "--goma-dir", goma_dir,
          "//out/Default"])

  build_with_goma_module(api)

  # annotated_steps step
  annotated_steps(api, build_properties.get('got_revision'))


def Linux_steps(api):
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "src"
  soln.url = "https://chromium.googlesource.com/chromium/src.git"
  soln.custom_deps = {'src/chrome/test/chromedriver/third_party/java_tests':
      'https://chromium.googlesource.com/chromium/deps/webdriver'}
  soln = src_cfg.solutions.add()
  soln.name = "src-internal"
  soln.url = "https://chrome-internal.googlesource.com/chrome/src-internal.git"
  soln.custom_deps = {'src/chrome/test/data/firefox2_searchplugins': None,
      'src/tools/grit/grit/test/data': None,
      'src/chrome/test/data/firefox3_searchplugins': None,
      'src/webkit/data/test_shell/plugins': None,
      'src/data/page_cycler': None,
      'src/data/mozilla_js_tests': None,
      'src/chrome/test/data/firefox2_profile/searchplugins': None,
      'src/data/esctf': None,
      'src/data/memory_test': None,
      'src/data/mach_ports': None,
      'src/webkit/data/xbm_decoder': None,
      'src/webkit/data/ico_decoder': None,
      'src/data/selenium_core': None,
      'src/chrome/test/data/ssl/certs': None,
      'src/chrome/test/data/osdd': None,
      'src/webkit/data/bmp_decoder': None,
      'src/chrome/test/data/firefox3_profile/searchplugins': None,
      'src/data/autodiscovery': None}
  src_cfg.got_revision_mapping.update({'src': 'got_revision',
    'src/third_party/WebKit': 'got_webkit_revision',
    'src/tools/swarming_client': 'got_swarming_client_revision',
    'src/v8': 'got_v8_revision'})
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout()
  build_properties = api.properties.legacy()
  build_properties.update(result.json.output.get('properties', {}))
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {'LANDMINES_VERBOSE': '1', 'DEPOT_TOOLS_UPDATE': '0'}
  with api.context(env=env):
    api.build.python("gclient runhooks wrapper",
        api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"))
  # meta build step
  goma_dir = api.goma.ensure_goma()
  api.python("meta build", api.path["checkout"].join("tools", "mb", "mb.py"),
      args=["gen", "-m", "chromium.chromedriver", "-b",
          build_properties.get('buildername'), "--goma-dir", goma_dir,
          "//out/Default"])

  build_with_goma_module(api)

  # strip binary
  api.m.step('strip', cmd=['strip', str(api.path['checkout'].join(
      'out', 'Default', 'chromedriver'))])

  # annotated_steps step
  annotated_steps(api, build_properties.get('got_revision'))


dispatch_directory = {
  'Linux32': Linux32_steps,
  'Mac 10.6': Mac_10_6_steps,
  'Win7': Win7_steps,
  'Linux': Linux_steps,
}


def annotated_steps(api, got_revision):
  api.build.python('chromedriver buildbot steps',
      api.package_repo_resource('scripts', 'tools', 'runit.py'),
      args=[
        '-s',
        api.package_repo_resource('scripts', 'slave', 'runtest.py'),
        '--run-python-script',
        api.path['checkout'].join('chrome', 'test', 'chromedriver',
                                  'run_buildbot_steps.py'),
        '--revision', got_revision
      ],
      allow_subannotations=True)


def RunSteps(api):
  if api.properties["buildername"] not in dispatch_directory:
    raise api.step.StepFailure("Builder unsupported by recipe.")
  else:
    dispatch_directory[api.properties["buildername"]](api)

def GenTests(api):
  yield (api.test('Linux32') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='Linux32') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('Mac_10_6') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='Mac 10.6') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('Win7') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='Win7') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('Linux') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='Linux') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('builder_not_in_dispatch_directory') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='nonexistent_builder') +
    api.properties(bot_id='TestSlave')
        )
