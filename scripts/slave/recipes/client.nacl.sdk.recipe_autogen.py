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


def sdk_multi_steps(api):
    build_properties = api.properties.legacy()
    # bot_update step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "src"
    soln.url = "https://chromium.googlesource.com/chromium/src.git"
    soln = src_cfg.solutions.add()
    soln.name = "src-internal"
    soln.url = "https://chrome-internal.googlesource.com/chrome/" + \
            "src-internal.git"
    soln.custom_deps = {'src/chrome/test/data/firefox2_searchplugins': None,
                        'src/tools/grit/grit/test/data': None,
                        'src/chrome/test/data/firefox3_searchplugins': None,
                        'src/webkit/data/test_shell/plugins': None,
                        'src/data/page_cycler': None,
                        'src/data/mozilla_js_tests': None,
                        'src/chrome/test/data/firefox2_profile/searchplugins':
                        None,
                        'src/data/esctf': None,
                        'src/data/memory_test': None,
                        'src/data/mach_ports': None,
                        'src/webkit/data/xbm_decoder': None,
                        'src/webkit/data/ico_decoder': None,
                        'src/data/selenium_core': None,
                        'src/chrome/test/data/ssl/certs': None,
                        'src/chrome/test/data/osdd': None,
                        'src/webkit/data/bmp_decoder': None,
                        'src/chrome/test/data/firefox3_profile/searchplugins':
                        None,
                        'src/data/autodiscovery': None}
    soln.custom_vars = {}
    src_cfg.got_revision_mapping.update(
        {'src': 'got_revision',
         'src/third_party/WebKit': 'got_webkit_revision',
         'src/tools/swarming_client': 'got_swarming_client_revision',
         'src/v8': 'got_v8_revision'})
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))

    api.chromium.ensure_goma()

    # clobber before runhooks
    api.file.rmtree('clobber', api.path['checkout'].join('out', 'Release'))

    # gclient runhooks step
    env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1',
           'LANDMINES_VERBOSE': '1',
           'DEPOT_TOOLS_UPDATE': '0',
           'GYP_DEFINES': 'fastbuild=1 component=static_library'}
    api.chromium.runhooks(env=env)

    # generate_build_files step
    api.chromium.run_mb(api.properties.get('mastername'),
                        api.properties.get('buildername'))

    # cleanup_temp step
    api.chromium.cleanup_temp()

    # compile step
    api.chromium.compile(['chrome'])

    # annotated_steps step
    api.python(
        "annotated_steps",
        api.path["build"].join("scripts", "slave", "chromium",
                               "nacl_sdk_buildbot_run.py"),
        allow_subannotations=True)


def sdk_multirel_steps(api):
    build_properties = api.properties.legacy()
    # update scripts step; implicitly run by recipe engine.
    # bot_update step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "chrome-official"
    soln.url = "svn://svn.chromium.org/chrome-internal/trunk/tools/buildspec/"+\
        "build/chrome-official"
    soln.custom_deps = {'src-pdf': None, 'src/pdf': None}
    src_cfg.got_revision_mapping.update(
        {'src': 'got_revision',
         'src/third_party/WebKit': 'got_webkit_revision',
         'src/tools/swarming_client': 'got_swarming_client_revision',
         'src/v8': 'got_v8_revision'})
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))

    api.chromium.ensure_goma()

    # clobber before runhooks
    api.file.rmtree('clobber', api.path['checkout'].join('out', 'Release'))

    # gclient runhooks step
    env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1',
           'LANDMINES_VERBOSE': '1',
           'DEPOT_TOOLS_UPDATE': '0',
           'GYP_DEFINES': 'fastbuild=1 component=static_library'}
    api.chromium.runhooks(env=env)

    # generate_build_files step
    api.chromium.run_mb(api.properties.get('mastername'),
                        api.properties.get('buildername'))

    # cleanup_temp step
    api.chromium.cleanup_temp()

    # compile step
    api.chromium.compile(['chrome'])

    # annotated_steps step
    api.python(
        "annotated_steps",
        api.path["build"].join("scripts", "slave", "chromium",
                               "nacl_sdk_buildbot_run.py"),
        allow_subannotations=True)



dispatch_directory = {
    'linux-sdk-multi': sdk_multi_steps,
    'mac-sdk-multi': sdk_multi_steps,
    'windows-sdk-multi': sdk_multi_steps,
    'linux-sdk-multirel': sdk_multirel_steps,
    'linux-sdk-asan-multi': sdk_multi_steps,
    'windows-sdk-multirel': sdk_multirel_steps,
    'mac-sdk-multirel': sdk_multirel_steps,
}


def RunSteps(api):
    if api.properties["buildername"] not in dispatch_directory:
        raise api.step.StepFailure("Builder unsupported by recipe.")
    else:
        api.chromium.set_config('chromium')
        api.chromium.ensure_goma()
        dispatch_directory[api.properties["buildername"]](api)


def GenTests(api):
    yield (api.test('linux_sdk_multi') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='linux-sdk-multi') +
           api.properties(revision='123456789abcdef') + api.properties(
               got_revision='123456789abcdef') + api.properties(
                   buildnumber='42') + api.properties(slavename='TestSlave'))
    yield (api.test('mac_sdk_multi') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='mac-sdk-multi') +
           api.properties(revision='123456789abcdef') + api.properties(
               got_revision='123456789abcdef') + api.properties(
                   buildnumber='42') + api.properties(slavename='TestSlave'))
    yield (api.test('windows_sdk_multi') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='windows-sdk-multi') +
           api.properties(revision='123456789abcdef') + api.properties(
               got_revision='123456789abcdef') + api.properties(
                   buildnumber='42') + api.properties(slavename='TestSlave'))
    yield (api.test('linux_sdk_multirel') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='linux-sdk-multirel') +
           api.properties(revision='123456789abcdef') + api.properties(
               got_revision='123456789abcdef') + api.properties(
                   buildnumber='42') + api.properties(slavename='TestSlave'))
    yield (api.test('linux_sdk_asan_multi') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='linux-sdk-asan-multi') +
           api.properties(revision='123456789abcdef') + api.properties(
               got_revision='123456789abcdef') + api.properties(
                   buildnumber='42') + api.properties(slavename='TestSlave'))
    yield (api.test('windows_sdk_multirel') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='windows-sdk-multirel') +
           api.properties(revision='123456789abcdef') + api.properties(
               got_revision='123456789abcdef') + api.properties(
                   buildnumber='42') + api.properties(slavename='TestSlave'))
    yield (api.test('mac_sdk_multirel') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='mac-sdk-multirel') +
           api.properties(revision='123456789abcdef') + api.properties(
               got_revision='123456789abcdef') + api.properties(
                   buildnumber='42') + api.properties(slavename='TestSlave'))
    yield (api.test('builder_not_in_dispatch_directory') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='nonexistent_builder') + api.properties(
                slavename='TestSlave'))
