# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]


def Android_ChromeDriver_Tests__dbg__steps(api):
    build_properties = api.properties.legacy()
    # update scripts step; implicitly run by recipe engine.
    # bot_update step
    src_cfg = api.gclient.make_config(GIT_MODE=True)
    soln = src_cfg.solutions.add()
    soln.name = "src"
    soln.url = "https://chromium.googlesource.com/chromium/src.git"
    soln.custom_deps = {
        'src/chrome/test/chromedriver/third_party/java_tests':
        'https://chromium.googlesource.com/chromium/deps/webdriver.git',
        'src/third_party/WebKit/LayoutTests': None
    }
    soln.custom_vars = {'webkit_trunk': 'http://src.chromium.org/blink/trunk',
                        'googlecode_url': 'http://%s.googlecode.com/svn',
                        'nacl_trunk':
                        'http://src.chromium.org/native_client/trunk',
                        'sourceforge_url':
                        'https://svn.code.sf.net/p/%(repo)s/code',
                        'llvm_url': 'http://llvm.org/svn/llvm-project'}
    src_cfg.target_os = set(['android'])
    src_cfg.got_revision_mapping.update(
        {'src': 'got_revision',
         'src/third_party/WebKit': 'got_webkit_revision',
         'src/tools/swarming_client': 'got_swarming_client_revision',
         'src/v8': 'got_v8_revision'})
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout(force=True)
    build_properties.update(result.json.output.get("properties", {}))
    # gclient revert step; made unnecessary by bot_update
    # gclient update step; made unnecessary by bot_update
    # cleanup_temp step
    api.chromium.cleanup_temp()
    # slave_steps step
    api.python(
        "slave_steps",
        "src/build/android/buildbot/bb_run_bot.py",
        args=
        ['--build-properties=%s' % api.json.dumps(build_properties,
                                                  separators=(',', ':')),
         ('--factory-properties={"GYP_DEFINES":" component=shared_library",'
          '"android_bot_id":"chromedriver-fyi-tests-dbg","build_url":'
          '"gs://chromium-fyi-archive/chromium.fyi/Android Builder (dbg)",'
          '"clobber":false,"gclient_env":{},"target":"Debug",'
          '"target_os":"android"}')],
        allow_subannotations=True)


def Android_Asan_Builder_Tests__dbg__steps(api):
    build_properties = api.properties.legacy()
    # update scripts step; implicitly run by recipe engine.
    # bot_update step
    src_cfg = api.gclient.make_config(GIT_MODE=True)
    soln = src_cfg.solutions.add()
    soln.name = "src"
    soln.url = "https://chromium.googlesource.com/chromium/src.git"
    soln.custom_deps = {'src/third_party/WebKit/LayoutTests': None}
    soln.custom_vars = {'webkit_trunk': 'http://src.chromium.org/blink/trunk',
                        'googlecode_url': 'http://%s.googlecode.com/svn',
                        'nacl_trunk':
                        'http://src.chromium.org/native_client/trunk',
                        'sourceforge_url':
                        'https://svn.code.sf.net/p/%(repo)s/code',
                        'llvm_url': 'http://llvm.org/svn/llvm-project'}
    src_cfg.target_os = set(['android'])
    src_cfg.got_revision_mapping.update(
        {'src': 'got_revision',
         'src/third_party/WebKit': 'got_webkit_revision',
         'src/tools/swarming_client': 'got_swarming_client_revision',
         'src/v8': 'got_v8_revision'})
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout(force=True)
    build_properties.update(result.json.output.get("properties", {}))
    # gclient revert step; made unnecessary by bot_update
    # gclient update step; made unnecessary by bot_update
    # cleanup_temp step
    api.chromium.cleanup_temp()
    # slave_steps step
    api.python(
        "slave_steps",
        "src/build/android/buildbot/bb_run_bot.py",
        args=
        ['--build-properties=%s' % api.json.dumps(build_properties,
                                                  separators=(',', ':')),
         ('--factory-properties={"GYP_DEFINES":" component=shared_library",'
          '"android_bot_id":"asan-builder-tests-dbg","clobber":false,'
          '"gclient_env":{},"target":"Debug","target_os":"android"}')],
        allow_subannotations=True)


def CFI_Linux_CF_steps(api):
    build_properties = api.properties.legacy()
    # update scripts step; implicitly run by recipe engine.
    # bot_update step
    src_cfg = api.gclient.make_config(GIT_MODE=True)
    soln = src_cfg.solutions.add()
    soln.name = "src"
    soln.url = "https://chromium.googlesource.com/chromium/src.git"
    soln.custom_deps = {'src/third_party/WebKit/LayoutTests': None}
    soln.custom_vars = {'webkit_trunk': 'http://src.chromium.org/blink/trunk',
                        'googlecode_url': 'http://%s.googlecode.com/svn',
                        'nacl_trunk':
                        'http://src.chromium.org/native_client/trunk',
                        'sourceforge_url':
                        'https://svn.code.sf.net/p/%(repo)s/code',
                        'llvm_url': 'http://llvm.org/svn/llvm-project'}
    src_cfg.got_revision_mapping.update(
        {'src': 'got_revision',
         'src/third_party/WebKit': 'got_webkit_revision',
         'src/tools/swarming_client': 'got_swarming_client_revision',
         'src/v8': 'got_v8_revision'})
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout(force=True)
    build_properties.update(result.json.output.get("properties", {}))
    # gclient revert step; made unnecessary by bot_update
    # gclient update step; made unnecessary by bot_update
    # gclient runhooks wrapper step
    env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1',
           'LANDMINES_VERBOSE': '1',
           'DEPOT_TOOLS_UPDATE': '0',
           'GYP_DEFINES': ' component=static_library',
           'LLVM_DOWNLOAD_GOLD_PLUGIN': '1'}
    api.python("gclient runhooks wrapper",
               api.path["build"].join("scripts", "slave",
                                      "runhooks_wrapper.py"),
               env=env)
    # cleanup_temp step
    api.chromium.cleanup_temp()
    # compile.py step
    args = ['--target', 'Release', '--clobber', 'chromium_builder_asan']
    api.python("compile",
               api.path["build"].join("scripts", "slave", "compile.py"),
               args=args)
    # ClusterFuzz Archive step
    # HACK(aneeshm): chromium_utils fails without this.
    build_properties["primary_repo"] = ""
    api.python(
        'ClusterFuzz Archive',
        api.path["build"].join("scripts", "slave", "chromium",
                               "cf_archive_build.py"),
        args=
        ['--target', 'Release', "--build-properties=%s" %
         api.json.dumps(build_properties,
                        separators=(',', ':')),
         ('--factory-properties={"blink_config":"chromium","cf_archive_build":'
          'true,"cf_archive_name":"cfi","gclient_env":'
          '{"CHROMIUM_GYP_SYNTAX_CHECK":"1","DEPOT_TOOLS_UPDATE":"0",'
          '"GYP_DEFINES":" component=static_library","LANDMINES_VERBOSE":"1",'
          '"LLVM_DOWNLOAD_GOLD_PLUGIN":"1"},"gs_acl":"public-read",'
          '"gs_bucket":"gs://chromium-browser-cfi"}')],
        cwd=api.path["slave_build"])


dispatch_directory = {
    'Android ChromeDriver Tests (dbg)': Android_ChromeDriver_Tests__dbg__steps,
    'Android Asan Builder Tests (dbg)': Android_Asan_Builder_Tests__dbg__steps,
    'CFI Linux CF': CFI_Linux_CF_steps,
}


def RunSteps(api):
    if api.properties["buildername"] not in dispatch_directory:
        raise api.step.StepFailure("Builder unsupported by recipe.")
    else:
        dispatch_directory[api.properties["buildername"]](api)


def GenTests(api):
  yield (api.test('Android_ChromeDriver_Tests__dbg_') +
    api.properties(mastername='chromium.fyi') +
    api.properties(buildername='Android ChromeDriver Tests (dbg)') +
    api.properties(revision='123456789abcdef') +
    api.properties(got_revision='123456789abcdef') +
    api.properties(buildnumber='42') +
    api.properties(slavename='TestSlave')
        )
  yield (api.test('Android_Asan_Builder_Tests__dbg_') +
    api.properties(mastername='chromium.fyi') +
    api.properties(buildername='Android Asan Builder Tests (dbg)') +
    api.properties(revision='123456789abcdef') +
    api.properties(got_revision='123456789abcdef') +
    api.properties(buildnumber='42') +
    api.properties(slavename='TestSlave')
        )
  yield (api.test('CFI_Linux_CF') +
    api.properties(mastername='chromium.fyi') +
    api.properties(buildername='CFI Linux CF') +
    api.properties(revision='123456789abcdef') +
    api.properties(got_revision='123456789abcdef') +
    api.properties(buildnumber='42') +
    api.properties(slavename='TestSlave')
        )
  yield (api.test('builder_not_in_dispatch_directory') +
    api.properties(mastername='chromium.fyi') +
    api.properties(buildername='nonexistent_builder') +
    api.properties(slavename='TestSlave')
        )
