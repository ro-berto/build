# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

DEPS = [
    'build',
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/context',
    'recipe_engine/file',
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
    src_cfg.got_revision_mapping.update(
        {'src': 'got_revision',
         'src/third_party/WebKit': 'got_webkit_revision',
         'src/tools/swarming_client': 'got_swarming_client_revision',
         'src/v8': 'got_v8_revision'})
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))

    # clobber before runhooks
    api.file.rmtree('clobber', api.path['checkout'].join('out', 'Release'))

    # gclient runhooks step
    env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1',
           'LANDMINES_VERBOSE': '1',
           'DEPOT_TOOLS_UPDATE': '0',
           'GYP_DEFINES': 'fastbuild=1 component=static_library'}
    with api.context(env=env):
      api.chromium.runhooks()

    # generate_build_files step
    _, raw_result = api.chromium.mb_gen(api.properties.get('mastername'),
            api.properties.get('buildername'))
    if raw_result.status != common_pb.SUCCESS:
        return raw_result

    # compile step
    raw_result = api.chromium.compile(['chrome'], use_goma_module=True)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result

    # annotated_steps step
    api.build.python(
        "annotated_steps",
        api.repo_resource("scripts", "slave", "chromium",
                               "nacl_sdk_buildbot_run.py"),
        allow_subannotations=True)


def sdk_multirel_steps(api):
    build_properties = api.properties.legacy()
    # update scripts step; implicitly run by recipe engine.
    # bot_update step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "src"
    soln.url = "https://chromium.googlesource.com/chromium/src.git"
    soln.deps_file = 'DEPS'
    src_cfg.got_revision_mapping.update(
        {'src': 'got_revision',
         'src/third_party/WebKit': 'got_webkit_revision',
         'src/tools/swarming_client': 'got_swarming_client_revision',
         'src/v8': 'got_v8_revision'})
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))

    # clobber before runhooks
    api.file.rmtree('clobber', api.path['checkout'].join('out', 'Release'))

    # gclient runhooks step
    env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1',
           'LANDMINES_VERBOSE': '1',
           'DEPOT_TOOLS_UPDATE': '0',
           'GYP_DEFINES': 'fastbuild=1 component=static_library'}
    with api.context(env=env):
      api.chromium.runhooks()

    # generate_build_files step
    _, raw_result = api.chromium.mb_gen(api.properties.get('mastername'),
                        api.properties.get('buildername'))
    if raw_result.status != common_pb.SUCCESS:
        return raw_result

    # compile step
    raw_result = api.chromium.compile(['chrome'], use_goma_module=True)
    if raw_result.status != common_pb.SUCCESS:
      return raw_result

    # annotated_steps step
    api.build.python(
        "annotated_steps",
        api.repo_resource("scripts", "slave", "chromium",
                               "nacl_sdk_buildbot_run.py"),
        allow_subannotations=True)



dispatch_directory = {
    'linux-sdk-multi': sdk_multi_steps,
    'mac-sdk-multi': sdk_multi_steps,
    'windows-sdk-multi': sdk_multi_steps,
    'linux-sdk-asan-multi': sdk_multi_steps,
    'linux-sdk-multirel': sdk_multirel_steps,
    'windows-sdk-multirel': sdk_multirel_steps,
    'mac-sdk-multirel': sdk_multirel_steps,
}


def RunSteps(api):
    buildername = api.properties["buildername"]
    if buildername not in dispatch_directory:
        raise api.step.StepFailure("Builder unsupported by recipe.")
    else:
        api.chromium.set_config('chromium')
        api.chromium.ensure_goma()
        return dispatch_directory[buildername](api)


def GenTests(api):
    yield (api.test('linux_sdk_multi') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='linux-sdk-multi') +
           api.properties(revision='a' * 40) + api.properties(
               got_revision='a' * 40) + api.properties(
                   buildnumber='42') + api.properties(bot_id='TestSlave'))
    yield (api.test('mac_sdk_multi') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='mac-sdk-multi') +
           api.properties(revision='a' * 40) + api.properties(
               got_revision='a' * 40) + api.properties(
                   buildnumber='42') + api.properties(bot_id='TestSlave'))
    yield (api.test('windows_sdk_multi') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='windows-sdk-multi') +
           api.properties(revision='a' * 40) + api.properties(
               got_revision='a' * 40) + api.properties(
                   buildnumber='42') + api.properties(bot_id='TestSlave'))
    yield (api.test('linux_sdk_multirel') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='linux-sdk-multirel') +
           api.properties(revision='a' * 40) + api.properties(
               got_revision='a' * 40) + api.properties(
                   buildnumber='42') + api.properties(bot_id='TestSlave'))
    yield (api.test('linux_sdk_asan_multi') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='linux-sdk-asan-multi') +
           api.properties(revision='a' * 40) + api.properties(
               got_revision='a' * 40) + api.properties(
                   buildnumber='42') + api.properties(bot_id='TestSlave'))
    yield (api.test('windows_sdk_multirel') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='windows-sdk-multirel') +
           api.properties(revision='a' * 40) + api.properties(
               got_revision='a' * 40) + api.properties(
                   buildnumber='42') + api.properties(bot_id='TestSlave'))
    yield (api.test('mac_sdk_multirel') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='mac-sdk-multirel') +
           api.properties(revision='a' * 40) + api.properties(
               got_revision='a' * 40) + api.properties(
                   buildnumber='42') + api.properties(bot_id='TestSlave'))
    yield (api.test('builder_not_in_dispatch_directory') + api.properties(
        mastername='client.nacl.sdk') + api.properties(
            buildername='nonexistent_builder') + api.properties(
                bot_id='TestSlave'))
    yield (
        api.test('compile_failure_multi') +
        api.properties(
            mastername='client.nacl.sdk',
            buildername='mac-sdk-multi',
            bot_id='TestSlave'
        ) +
        api.step_data('compile', retcode=1) +
        api.post_process(post_process.StatusFailure) +
        api.post_process(post_process.DropExpectation)
    )
    yield (
        api.test('compile_failure_multirel') +
        api.properties(
            mastername='client.nacl.sdk',
            buildername='mac-sdk-multirel',
            bot_id='TestSlave'
        ) +
        api.step_data('compile', retcode=1) +
        api.post_process(post_process.StatusFailure) +
        api.post_process(post_process.DropExpectation)
    )
    yield (
        api.test('mb_gen_multi_failure') +
        api.properties(
            mastername='client.nacl.sdk',
            buildername='mac-sdk-multi',
            revision='a' * 40,
            got_revision='a' * 40,
            buildnumber='42',
            bot_id='TestSlave'
        ) +
        api.step_data('generate_build_files', retcode=1) +
        api.post_process(post_process.StatusFailure) +
        api.post_process(post_process.DropExpectation)
    )
    yield (
        api.test('mb_gen_multirel_failure') +
        api.properties(
            mastername='client.nacl.sdk',
            buildername='mac-sdk-multirel',
            revision='a' * 40,
            got_revision='a' * 40,
            buildnumber='42',
            bot_id='TestSlave'
        ) +
        api.step_data('generate_build_files', retcode=1) +
        api.post_process(post_process.StatusFailure) +
        api.post_process(post_process.DropExpectation)
    )
