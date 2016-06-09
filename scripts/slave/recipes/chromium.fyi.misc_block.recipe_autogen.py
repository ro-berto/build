# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'file',
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


dispatch_directory = {
    'Android ChromeDriver Tests (dbg)': Android_ChromeDriver_Tests__dbg__steps,
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
  yield (api.test('builder_not_in_dispatch_directory') +
    api.properties(mastername='chromium.fyi') +
    api.properties(buildername='nonexistent_builder') +
    api.properties(slavename='TestSlave')
        )
