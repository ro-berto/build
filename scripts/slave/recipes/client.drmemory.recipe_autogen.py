# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'file',
    'gsutil',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def linux_builder_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # get buildnumber step; no longer needed
    # Package DrMemory step
    api.step("Package Dr. Memory",
             ["ctest", "-VV", "-S",
              str(api.path["checkout"].join("package.cmake")) + ",build=0x" +
              build_properties["got_revision"][:7] + ";drmem_only"])
    # find package file step; no longer necessary
    # upload drmemory build step
    api.gsutil.upload("DrMemory-Linux-*" + build_properties["got_revision"][
                      :7] + ".tar.gz", "chromium-drmemory-builds", "builds/")


def linux_lucid_x64_drm_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # Dr. Memory ctest step
    api.step(
        "Dr. Memory ctest",
        ["ctest", "--timeout", "60", "-VV", "-S",
         str(api.path["checkout"].join("tests", "runsuite.cmake")) +
         ",drmemory_only;long;build=0x" + build_properties["got_revision"][:7]
         ])
    # Prepare to pack test results step; null converted
    # Pack test results step
    api.step("Pack test results",
             ['7z', 'a', '-xr!*.pdb',
              "testlogs_r" + build_properties["got_revision"] + "_b" +
              str(build_properties["buildnumber"]) + ".7z",
              'build_drmemory-dbg-32/logs',
              'build_drmemory-dbg-32/Testing/Temporary',
              'build_drmemory-rel-32/logs',
              'build_drmemory-rel-32/Testing/Temporary',
              'build_drmemory-dbg-64/logs',
              'build_drmemory-dbg-64/Testing/Temporary',
              'build_drmemory-rel-64/logs',
              'build_drmemory-rel-64/Testing/Temporary', 'xml:results'])
    # upload drmemory test logs step
    api.gsutil.upload("testlogs_r" + build_properties["got_revision"] + "_b" +
                      str(api.properties[
                          "buildnumber"]) + ".7z", "chromium-drmemory-builds",
                      "testlogs/from_%s" % api.properties["buildername"])


def win_vista_x64_drm_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # clear tools directory step; null converted
    # update tools step; null converted
    # unpack tools step; generic ShellCommand converted
    api.step("unpack tools",
             [api.path["start_dir"].join('tools', 'buildbot', 'bot_tools',
               'unpack.bat')],
             env={},
             cwd=api.path[
                 "start_dir"].join('tools', 'buildbot', 'bot_tools'))
    # windows Dr. Memory ctest step
    api.step("Dr. Memory ctest",
             [api.package_repo_resource("scripts", "slave", "drmemory",
                                     "build_env.bat"), 'ctest', '--timeout',
              '60', '-VV', '-S',
              str(api.path["checkout"].join("tests", "runsuite.cmake")) +
              ",drmemory_only;long;build=" +
              str(build_properties["buildnumber"])])
    # Checkout TSan tests step
    api.step("Checkout TSan tests",
             ['svn', 'checkout', '--force',
              'http://data-race-test.googlecode.com/svn/trunk/',
              api.path["start_dir"].join("tsan")])
    # Build TSan tests step
    api.step("Build TSan Tests",
             ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat', 'make',
              '-C', api.path["start_dir"].join("tsan", "unittest")],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools"),
                  "CYGWIN": "nodosfilewarning"})
    # Dr. Memory TSan test step
    api.step(
        "dbg full TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "dbg light TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "-light", "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "rel full TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-rel-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "rel light TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-rel-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "-light", "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "dbg full nosyms TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Prepare to pack test results step; null converted
    # Pack test results step
    api.step("Pack test results",
             [api.package_repo_resource("scripts", "slave", "drmemory",
               "build_env.bat"),'7z', 'a', '-xr!*.pdb',
              "testlogs_r" + build_properties["got_revision"] + "_b" +
              str(build_properties["buildnumber"]) + ".7z",
              'build_drmemory-dbg-32/logs',
              'build_drmemory-dbg-32/Testing/Temporary',
              'build_drmemory-rel-32/logs',
              'build_drmemory-rel-32/Testing/Temporary',
              'build_drmemory-dbg-64/logs',
              'build_drmemory-dbg-64/Testing/Temporary',
              'build_drmemory-rel-64/logs',
              'build_drmemory-rel-64/Testing/Temporary', 'xmlresults'],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools")})
    # upload drmemory test logs step
    api.gsutil.upload("testlogs_r" + build_properties["got_revision"] + "_b" +
                      str(api.properties[
                          "buildnumber"]) + ".7z", "chromium-drmemory-builds",
                      "testlogs/from_%s" % api.properties["buildername"])


def mac_mavericks_x64_DR_steps(api):
    build_properties = api.properties.legacy()
    # checkout DynamiRIO step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "dynamorio"
    soln.url = "https://github.com/DynamoRIO/dynamorio.git"
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # pre-commit suite step
    api.step("pre-commit suite",
             ['ctest', '--timeout', '120', '-VV', '-S', api.path[
                 "checkout"].join("suite", "runsuite.cmake")],
             cwd=api.path["start_dir"],
             ok_ret="all")


def linux_cr_builder_steps(api):
    build_properties = api.properties.legacy()
    # update scripts step; implicitly run by recipe engine.
    # bot_update step
    src_cfg = api.gclient.make_config()
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
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))

    # clobber before runhooks
    if 'clobber' in api.properties:
      api.file.rmtree('clobber', api.path['checkout'].join('out', 'Release'))

    # gclient revert step; made unnecessary by bot_update
    # gclient update step; made unnecessary by bot_update
    # gclient runhooks wrapper step
    env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1',
           'GYP_GENERATORS': 'ninja',
           'DEPOT_TOOLS_UPDATE': '0',
           'GYP_DEFINES': 'build_for_tool=drmemory component=shared_library',
           'LANDMINES_VERBOSE': '1'}
    api.python("gclient runhooks wrapper",
               api.package_repo_resource("scripts", "slave",
                                      "runhooks_wrapper.py"),
               env=env)
    # cleanup_temp step
    api.chromium.cleanup_temp()
    # compile.py step
    args = ['--target', 'Release', '--build-tool=ninja', '--compiler=goma',
            'content_shell', 'base_unittests', 'browser_tests',
            'crypto_unittests', 'ipc_tests', 'media_unittests',
            'net_unittests', 'printing_unittests', 'remoting_unittests',
            'sql_unittests', 'unit_tests', 'url_unittests']
    api.python("compile",
               api.package_repo_resource("scripts", "slave", "compile.py"),
               args=args)


def mac_builder_DR_steps(api):
    build_properties = api.properties.legacy()
    # checkout DynamiRIO step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "dynamorio"
    soln.url = "https://github.com/DynamoRIO/dynamorio.git"
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # get buildnumber step; no longer needed
    # Package DynamoRIO step
    api.step("Package DynamoRIO",
             ["ctest", "-VV", "-S",
              str(api.path["checkout"].join("make", "package.cmake")) +
              ",build=0x" + build_properties["revision"][:7]])
    # find package file step; no longer necessary
    # upload dynamorio package
    api.gsutil.upload("DynamoRIO-MacOS-*" + build_properties["got_revision"][
                      :7] + ".tar.gz", "chromium-dynamorio", "builds/")


def win_xp_drm_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # clear tools directory step; null converted
    # update tools step; null converted
    # unpack tools step; generic ShellCommand converted
    api.step("unpack tools",
             [api.path["start_dir"].join('tools', 'buildbot', 'bot_tools',
               'unpack.bat')],
             env={},
             cwd=api.path[
                 "start_dir"].join('tools', 'buildbot', 'bot_tools'))
    # windows Dr. Memory ctest step
    api.step("Dr. Memory ctest",
             [api.package_repo_resource("scripts", "slave", "drmemory",
                                     "build_env.bat"), 'ctest', '--timeout',
              '60', '-VV', '-S',
              str(api.path["checkout"].join("tests", "runsuite.cmake")) +
              ",drmemory_only;long;build=" +
              str(build_properties["buildnumber"])])
    # Checkout TSan tests step
    api.step("Checkout TSan tests",
             ['svn', 'checkout', '--force',
              'http://data-race-test.googlecode.com/svn/trunk/',
              api.path["start_dir"].join("tsan")])
    # Build TSan tests step
    api.step("Build TSan Tests",
             ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat', 'make',
              '-C', api.path["start_dir"].join("tsan", "unittest")],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools"),
                  "CYGWIN": "nodosfilewarning"})
    # Dr. Memory TSan test step
    api.step(
        "dbg full TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "dbg light TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "-light", "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "rel full TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-rel-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "rel light TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-rel-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "-light", "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "dbg full nosyms TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Prepare to pack test results step; null converted
    # Pack test results step
    api.step("Pack test results",
             [api.package_repo_resource("scripts", "slave", "drmemory",
               "build_env.bat"), '7z', 'a', '-xr!*.pdb',
              "testlogs_r" + build_properties["got_revision"] + "_b" +
              str(build_properties["buildnumber"]) + ".7z",
              'build_drmemory-dbg-32/logs',
              'build_drmemory-dbg-32/Testing/Temporary',
              'build_drmemory-rel-32/logs',
              'build_drmemory-rel-32/Testing/Temporary',
              'build_drmemory-dbg-64/logs',
              'build_drmemory-dbg-64/Testing/Temporary',
              'build_drmemory-rel-64/logs',
              'build_drmemory-rel-64/Testing/Temporary', 'xmlresults'],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools")})
    # upload drmemory test logs step
    api.gsutil.upload("testlogs_r" + build_properties["got_revision"] + "_b" +
                      str(api.properties[
                          "buildnumber"]) + ".7z", "chromium-drmemory-builds",
                      "testlogs/from_%s" % api.properties["buildername"])


def mac_mavericks_x64_drm_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # Dr. Memory ctest step
    api.step(
        "Dr. Memory ctest",
        ["ctest", "--timeout", "60", "-VV", "-S",
         str(api.path["checkout"].join("tests", "runsuite.cmake")) +
         ",drmemory_only;long;build=0x" + build_properties["got_revision"][:7]
         ])
    # Prepare to pack test results step; null converted
    # Pack test results step
    api.step("Pack test results",
             ['7z', 'a', '-xr!*.pdb',
              "testlogs_r" + build_properties["got_revision"] + "_b" +
              str(build_properties["buildnumber"]) + ".7z",
              'build_drmemory-dbg-32/logs',
              'build_drmemory-dbg-32/Testing/Temporary',
              'build_drmemory-rel-32/logs',
              'build_drmemory-rel-32/Testing/Temporary', 'xml:results'])
    # upload drmemory test logs step
    api.gsutil.upload("testlogs_r" + build_properties["got_revision"] + "_b" +
                      str(api.properties[
                          "buildnumber"]) + ".7z", "chromium-drmemory-builds",
                      "testlogs/from_%s" % api.properties["buildername"])


def linux_cr_steps(api):
    build_properties = api.properties.legacy()
    # checkout DynamiRIO step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "dynamorio"
    soln.url = "https://github.com/DynamoRIO/dynamorio.git"
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # Make the build directory step
    api.file.makedirs("makedirs", api.path["start_dir"].join("dynamorio"))
    api.file.makedirs("makedirs", api.path["start_dir"].join("dynamorio",
      "build"))
    # Configure release DynamoRIO step; generic ShellCommand converted
    api.step("Configure release DynamoRIO",
             [
                 'cmake', '..', '-DDEBUG=OFF'
             ],
             env={},
             cwd=api.path["start_dir"].join('dynamorio', 'build'))
    # Compile release DynamoRIO step; generic ShellCommand converted
    api.step("Compile release DynamoRIO",
             [
                 'make', '-j5'
             ],
             env={},
             cwd=api.path["start_dir"].join('dynamorio', 'build'))
    # don't follow python step; generic ShellCommand converted
    api.step("don't follow python",
             ['bin64/drconfig', '-reg', 'python', '-norun', '-v'],
             env={},
             cwd=api.path["start_dir"].join('dynamorio', 'build'))
    # drmemory test step
    api.step("content_shell",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/content_shell',
              '--run-layout-test', 'file:///home/chrome-bot/bb.html'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step("base_unittests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/base_unittests',
              '--gtest_filter=-TraceEventTestFixture.TraceContinuousSampling'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step("browser_tests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/browser_tests',
              '--gtest_filter=AutofillTest.BasicFormFill'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step("crypto_unittests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/crypto_unittests'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step("ipc_tests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/ipc_tests'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step("media_unittests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/media_unittests'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step("net_unittests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/net_unittests',
              '--gtest_filter=-CertDatabaseNSSTest.ImportCACertHierarchy*'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step(
        "printing_unittests",
        ['xvfb-run', '-a',
         api.path["checkout"].join("build", "bin64", "drrun"), '-stderr_mask',
         '12', '--',
         '../../linux-cr-builder/build/src/out/Release/printing_unittests'],
        env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
        cwd=api.path["checkout"])
    # drmemory test step
    api.step(
        "remoting_unittests",
        ['xvfb-run', '-a',
         api.path["checkout"].join("build", "bin64", "drrun"), '-stderr_mask',
         '12', '--',
         '../../linux-cr-builder/build/src/out/Release/remoting_unittests',
         '--gtest_filter='
         '-VideoFrameCapturerTest.Capture:DesktopProcessTest.DeathTest'
         ],
        env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
        cwd=api.path["checkout"])
    # drmemory test step
    api.step("sql_unittests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/sql_unittests'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step("unit_tests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/unit_tests'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])
    # drmemory test step
    api.step("url_unittests",
             ['xvfb-run', '-a',
              api.path["checkout"].join("build", "bin64", "drrun"),
              '-stderr_mask', '12', '--',
              '../../linux-cr-builder/build/src/out/Release/url_unittests'],
             env={'CHROME_DEVEL_SANDBOX': '/opt/chromium/chrome_sandbox'},
             cwd=api.path["checkout"])


def win8_cr_builder_steps(api):
    build_properties = api.properties.legacy()
    # svnkill step; not necessary in recipes
    # update scripts step; implicitly run by recipe engine.
    # taskkill step
    api.python("taskkill", api.package_repo_resource("scripts", "slave",
                                                  "kill_processes.py"))
    # bot_update step
    src_cfg = api.gclient.make_config()
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
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))

    # clobber before runhooks
    if 'clobber' in api.properties:
      api.file.rmtree('clobber', api.path['checkout'].join('out', 'Debug'))

    # gclient revert step; made unnecessary by bot_update
    # gclient update step; made unnecessary by bot_update
    # gclient runhooks wrapper step
    env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1',
           'LANDMINES_VERBOSE': '1',
           'DEPOT_TOOLS_UPDATE': '0',
           'GYP_DEFINES': 'build_for_tool=drmemory component=shared_library'}
    api.python("gclient runhooks wrapper",
               api.package_repo_resource("scripts", "slave",
                                      "runhooks_wrapper.py"),
               env=env)
    # cleanup_temp step
    api.chromium.cleanup_temp()
    # compile.py step
    args = ['--target', 'Debug', 'chromium_builder_dbg_drmemory_win']
    api.step("compile", ["python_slave", api.package_repo_resource(
        "scripts", "slave", "compile.py")] + args)


def win8_cr_steps(api):
    build_properties = api.properties.legacy()
    # Download build step
    api.gsutil.download("chromium-drmemory-builds",
                        "drmemory-windows-latest-sfx.exe",
                        "drm-sfx.exe",
                        cwd=api.path["start_dir"])
    # Unpack the build step; generic ShellCommand converted
    api.step("Unpack the build",
             [
                 'drm-sfx', '-ounpacked', '-y'
             ],
             env={},
             cwd=api.path["start_dir"])
    # Dr. Memory get revision step
    step_result = api.step("Get the revision number",
                           [
                               'unpacked\\bin\\drmemory', '-version'
                           ],
                           stdout=api.raw_io.output())
    build_properties["got_revision"] = step_result.stdout.split()[3].\
        split(".")[2]
    # Chromium 'url' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'url' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'url', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'printing' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'printing' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'printing', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'media' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'media' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'media', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'sql' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'sql' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'sql', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'crypto_unittests' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'crypto_unittests' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'crypto_unittests', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'remoting' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'remoting' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'remoting', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'ipc_tests' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'ipc_tests' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'ipc_tests', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'base_unittests' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'base_unittests' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'base_unittests', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'net' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'net' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'net', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'unit' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'unit' tests",
      ['..\\..\\win8-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'unit', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])


def win7_cr_steps(api):
    build_properties = api.properties.legacy()
    # Download build step
    api.gsutil.download("chromium-drmemory-builds",
                        "drmemory-windows-latest-sfx.exe",
                        "drm-sfx.exe",
                        cwd=api.path["start_dir"])
    # Unpack the build step; generic ShellCommand converted
    api.step("Unpack the build",
             [
                 'drm-sfx', '-ounpacked', '-y'
             ],
             env={},
             cwd=api.path["start_dir"])
    # Dr. Memory get revision step
    step_result = api.step("Get the revision number",
                           [
                               'unpacked\\bin\\drmemory', '-version'
                           ],
                           stdout=api.raw_io.output())
    build_properties["got_revision"] = step_result.stdout.split()[3].\
        split(".")[2]
    # Chromium 'url' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'url' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'url', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'printing' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'printing' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'printing', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'media' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'media' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'media', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'sql' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'sql' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'sql', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'crypto_unittests' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'crypto_unittests' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'crypto_unittests', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'remoting' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'remoting' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'remoting', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'ipc_tests' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'ipc_tests' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'ipc_tests', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'base_unittests' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'base_unittests' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'base_unittests', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'net' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'net' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'net', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])
    # Chromium 'unit' tests step; generic ShellCommand converted
    api.step(
      "Chromium 'unit' tests",
      ['..\\..\\win7-cr-builder\\build\\src\\tools\\valgrind\\chrome_tests.bat',
       '-t', 'unit', '--tool', 'drmemory_light', '--keep_logs'],
      env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
      cwd=api.path["start_dir"])


def win_8_x64_drm_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # clear tools directory step; null converted
    # update tools step; null converted
    # unpack tools step; generic ShellCommand converted
    api.step("unpack tools",
             [api.path["start_dir"].join('tools', 'buildbot', 'bot_tools',
               'unpack.bat')],
             env={},
             cwd=api.path[
                 "start_dir"].join('tools', 'buildbot', 'bot_tools'))
    # windows Dr. Memory ctest step
    api.step("Dr. Memory ctest",
             [api.package_repo_resource("scripts", "slave", "drmemory",
                                     "build_env.bat"), 'ctest', '--timeout',
              '60', '-VV', '-S',
              str(api.path["checkout"].join("tests", "runsuite.cmake")) +
              ",drmemory_only;long;build=" +
              str(build_properties["buildnumber"])])
    # Checkout TSan tests step
    api.step("Checkout TSan tests",
             ['svn', 'checkout', '--force',
              'http://data-race-test.googlecode.com/svn/trunk/',
              api.path["start_dir"].join("tsan")])
    # Build TSan tests step
    api.step("Build TSan Tests",
             ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat', 'make',
              '-C', api.path["start_dir"].join("tsan", "unittest")],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools"),
                  "CYGWIN": "nodosfilewarning"})
    # Dr. Memory TSan test step
    api.step(
        "dbg full TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "dbg light TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "-light", "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "rel full TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-rel-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "rel light TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-rel-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "-light", "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "dbg full nosyms TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Prepare to pack test results step; null converted
    # Pack test results step
    api.step("Pack test results",
             [api.package_repo_resource("scripts", "slave", "drmemory",
               "build_env.bat"), '7z', 'a', '-xr!*.pdb',
              "testlogs_r" + build_properties["got_revision"] + "_b" +
              str(build_properties["buildnumber"]) + ".7z",
              'build_drmemory-dbg-32/logs',
              'build_drmemory-dbg-32/Testing/Temporary',
              'build_drmemory-rel-32/logs',
              'build_drmemory-rel-32/Testing/Temporary',
              'build_drmemory-dbg-64/logs',
              'build_drmemory-dbg-64/Testing/Temporary',
              'build_drmemory-rel-64/logs',
              'build_drmemory-rel-64/Testing/Temporary', 'xmlresults'],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools")})
    # upload drmemory test logs step
    api.gsutil.upload("testlogs_r" + build_properties["got_revision"] + "_b" +
                      str(api.properties[
                          "buildnumber"]) + ".7z", "chromium-drmemory-builds",
                      "testlogs/from_%s" % api.properties["buildername"])


def win7_cr_builder_steps(api):
    build_properties = api.properties.legacy()
    # svnkill step; not necessary in recipes
    # update scripts step; implicitly run by recipe engine.
    # taskkill step
    api.python("taskkill", api.package_repo_resource("scripts", "slave",
                                                  "kill_processes.py"))
    # bot_update step
    src_cfg = api.gclient.make_config()
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
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))

    # clobber before runhooks
    if 'clobber' in api.properties:
      api.file.rmtree('clobber', api.path['checkout'].join('out', 'Debug'))

    # gclient revert step; made unnecessary by bot_update
    # gclient update step; made unnecessary by bot_update
    # gclient runhooks wrapper step
    env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1',
           'LANDMINES_VERBOSE': '1',
           'DEPOT_TOOLS_UPDATE': '0',
           'GYP_DEFINES': 'build_for_tool=drmemory component=shared_library'}
    api.python("gclient runhooks wrapper",
               api.package_repo_resource("scripts", "slave",
                                      "runhooks_wrapper.py"),
               env=env)
    # cleanup_temp step
    api.chromium.cleanup_temp()
    # compile.py step
    args = ['--target', 'Debug', 'chromium_builder_dbg_drmemory_win']
    api.step("compile", ["python_slave", api.package_repo_resource(
        "scripts", "slave", "compile.py")] + args)


def win_7_x64_drm_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # clear tools directory step; null converted
    # update tools step; null converted
    # unpack tools step; generic ShellCommand converted
    api.step("unpack tools",
             [api.path["start_dir"].join('tools', 'buildbot', 'bot_tools',
               'unpack.bat')],
             env={},
             cwd=api.path[
                 "start_dir"].join('tools', 'buildbot', 'bot_tools'))
    # windows Dr. Memory ctest step
    api.step("Dr. Memory ctest",
             [api.package_repo_resource("scripts", "slave", "drmemory",
                                     "build_env.bat"), 'ctest', '--timeout',
              '60', '-VV', '-S',
              str(api.path["checkout"].join("tests", "runsuite.cmake")) +
              ",drmemory_only;long;build=" +
              str(build_properties["buildnumber"])])
    # Checkout TSan tests step
    api.step("Checkout TSan tests",
             ['svn', 'checkout', '--force',
              'http://data-race-test.googlecode.com/svn/trunk/',
              api.path["start_dir"].join("tsan")])
    # Build TSan tests step
    api.step("Build TSan Tests",
             ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat', 'make',
              '-C', api.path["start_dir"].join("tsan", "unittest")],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools"),
                  "CYGWIN": "nodosfilewarning"})
    # Dr. Memory TSan test step
    api.step(
        "dbg full TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "dbg light TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "-light", "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "rel full TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-rel-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "rel light TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-rel-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "-light", "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Dr. Memory TSan test step
    api.step(
        "dbg full nosyms TSan tests",
        [api.package_repo_resource("scripts", "slave", "drmemory",
                                "build_env.bat"),
         'build_drmemory-dbg-32\\bin\\drmemory', '-dr_ops',
         '-msgbox_mask 0 -stderr_mask 15', '-results_to_stderr', '-batch',
         '-suppress', api.path["checkout"].join(
             "tests", "app_suite", "default-suppressions.txt"), "--",
         api.path["start_dir"].join("tsan", 'unittest', 'bin',
                                      'racecheck_unittest-windows-x86-O0.exe'),
         '--gtest_filter='
         '-PositiveTests.FreeVsRead:NegativeTests.WaitForMultiple*',
         '-147'],
        env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                      "bot_tools")})
    # Prepare to pack test results step; null converted
    # Pack test results step
    api.step("Pack test results",
             [api.package_repo_resource("scripts", "slave", "drmemory",
               "build_env.bat"), '7z', 'a', '-xr!*.pdb',
              "testlogs_r" + build_properties["got_revision"] + "_b" +
              str(build_properties["buildnumber"]) + ".7z",
              'build_drmemory-dbg-32/logs',
              'build_drmemory-dbg-32/Testing/Temporary',
              'build_drmemory-rel-32/logs',
              'build_drmemory-rel-32/Testing/Temporary',
              'build_drmemory-dbg-64/logs',
              'build_drmemory-dbg-64/Testing/Temporary',
              'build_drmemory-rel-64/logs',
              'build_drmemory-rel-64/Testing/Temporary', 'xmlresults'],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools")})
    # upload drmemory test logs step
    api.gsutil.upload("testlogs_r" + build_properties["got_revision"] + "_b" +
                      str(api.properties[
                          "buildnumber"]) + ".7z", "chromium-drmemory-builds",
                      "testlogs/from_%s" % api.properties["buildername"])


def mac_builder_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # get buildnumber step; no longer needed
    # Package DrMemory step
    api.step("Package Dr. Memory",
             ["ctest", "-VV", "-S",
              str(api.path["checkout"].join("package.cmake")) + ",build=0x" +
              build_properties["got_revision"][:7] + ";drmem_only"])
    # find package file step; no longer necessary
    # upload drmemory build step
    api.gsutil.upload("DrMemory-MacOS-*" + build_properties["got_revision"][
                      :7] + ".tar.gz", "chromium-drmemory-builds", "builds/")


def win_builder_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # clear tools directory step; null converted
    # update tools step; null converted
    # unpack tools step; generic ShellCommand converted
    api.step("unpack tools",
             [api.path["start_dir"].join('tools', 'buildbot', 'bot_tools',
               'unpack.bat')],
             env={},
             cwd=api.path[
                 "start_dir"].join('tools', 'buildbot', 'bot_tools'))
    # get buildnumber step; no longer needed
    # Package dynamorio step
    api.step("Package Dr. Memory",
             [api.package_repo_resource("scripts", "slave", "drmemory",
                                     "build_env.bat"), 'ctest', '-VV', '-S',
              str(api.path["checkout"].join("package.cmake")) + ",build=0x" +
              build_properties["got_revision"][:7] + ";drmem_only"],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools")},
             cwd=api.path["start_dir"])
    # Find package basename step
    step_result = api.step("Find package basename",
                           ["cmd.exe", "/C", "dir", "/O-D", "/B",
                            "DrMemory-Windows-*0x" + build_properties[
                                "got_revision"][:7] + ".zip"],
                           stdout=api.raw_io.output(),
                           cwd=api.path["start_dir"])
    # There can be multiple if we've done test builds so grab the first
    # line (we sorted by date with /O-D):
    basename = step_result.stdout.split()[0][:-4]
    # Delete prior sfx archive step
    api.file.remove("Delete prior sfx archive",
        api.path["start_dir"].join(basename + "-sfx.exe"),
        ok_ret=(0,1))
    # Create sfx archive step
    lastdir = api.path.basename(api.path["start_dir"])
    api.step("create sfx archive",
             [api.package_repo_resource("scripts", "slave", "drmemory",
                                     "build_env.bat"), "7z", "a", "-sfx",
              basename + "-sfx.exe",
              # To get the archive to contain paths relative to the
              # ...\\ZIP\\basename\\ dir we pass ..\\lastdir:
              api.path.join(
                '..', lastdir, 'build_drmemory-debug-32', '_CPack_Packages',
                'Windows', 'ZIP', basename, '*')],
             cwd=api.path["start_dir"],
             env={"BOTTOOLS": api.path["start_dir"].join("tools", "buildbot",
                                                           "bot_tools")})
    # upload latest build step
    api.file.copy("copy locally",
        api.path["start_dir"].join(basename + "-sfx.exe"),
        api.path["start_dir"].join("drmemory-windows-latest-sfx.exe"))
    api.gsutil.upload("drmemory-windows-latest-sfx.exe",
                      "chromium-drmemory-builds",
                      "",
                      cwd=api.path["start_dir"])
    # upload drmemory build step
    api.gsutil.upload("DrMemory-Windows-*" + build_properties["got_revision"][
                      :7] + ".zip", "chromium-drmemory-builds", "builds/")


dispatch_directory = {
    'linux-builder': linux_builder_steps,
    'linux-lucid_x64-drm': linux_lucid_x64_drm_steps,
    'win-vista_x64-drm': win_vista_x64_drm_steps,
    'mac-mavericks_x64-DR': mac_mavericks_x64_DR_steps,
    'linux-cr-builder': linux_cr_builder_steps,
    'mac-builder-DR': mac_builder_DR_steps,
    'win-xp-drm': win_xp_drm_steps,
    'mac-mavericks_x64-drm': mac_mavericks_x64_drm_steps,
    'linux-cr': linux_cr_steps,
    'win8-cr-builder': win8_cr_builder_steps,
    'win8-cr': win8_cr_steps,
    'win7-cr': win7_cr_steps,
    'win-8_x64-drm': win_8_x64_drm_steps,
    'win7-cr-builder': win7_cr_builder_steps,
    'win-7_x64-drm': win_7_x64_drm_steps,
    'mac-builder': mac_builder_steps,
    'win-builder': win_builder_steps,
}


def RunSteps(api):
    if api.properties["buildername"] not in dispatch_directory:
        raise api.step.StepFailure("Builder unsupported by recipe.")
    else:
        dispatch_directory[api.properties["buildername"]](api)


def GenTests(api):
  yield (api.test('linux_builder')
     + api.properties(
       mastername='client.drmemory',
       buildername='linux-builder',
       revision='123456789abcdef',
       got_revision='123456789abcdef',
       buildnumber=42,
       slavename='TestSlave',
     )
  )

  yield (api.test('linux_lucid_x64_drm')
    + api.properties(
      mastername='client.drmemory',
      buildername='linux-lucid_x64-drm',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('linux', 64)
  )

  yield (api.test('win_vista_x64_drm')
    + api.properties(
      mastername='client.drmemory',
      buildername='win-vista_x64-drm',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('win', 64)
  )

  yield (api.test('mac_mavericks_x64_DR')
    + api.properties(
      mastername='client.drmemory',
      buildername='mac-mavericks_x64-DR',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('mac', 64)
  )

  yield (api.test('linux_cr_builder')
    + api.properties(
      mastername='client.drmemory',
      buildername='linux-cr-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
  )

  yield (api.test('linux_cr_builder_clobber')
    + api.properties(
      mastername='client.drmemory',
      buildername='linux-cr-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
      clobber='',
    )
  )

  yield (api.test('mac_builder_DR')
    + api.properties(
      mastername='client.drmemory',
      buildername='mac-builder-DR',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('mac', 64)
  )

  yield (api.test('win_xp_drm')
    + api.properties(
      mastername='client.drmemory',
      buildername='win-xp-drm',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('win', 32)
  )

  yield (api.test('mac_mavericks_x64_drm')
    + api.properties(
      mastername='client.drmemory',
      buildername='mac-mavericks_x64-drm',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('mac', 64)
  )

  yield (api.test('linux_cr')
    + api.properties(
      mastername='client.drmemory',
      buildername='linux-cr',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
  )

  yield (api.test('win8_cr_builder')
    + api.properties(
      mastername='client.drmemory',
      buildername='win8-cr-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('win', 64)
  )

  yield (api.test('win8_cr_builder_clobber')
    + api.properties(
      mastername='client.drmemory',
      buildername='win8-cr-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
      clobber='',
    )
    + api.platform('win', 64)
  )

  yield (api.test('win8_cr')
    + api.properties(
      mastername='client.drmemory',
      buildername='win8-cr',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.step_data("Get the revision number",
      stdout=api.raw_io.output("Dr. Memory version 1.9.16845"
        " -- build 178560794"))
    + api.platform('win', 64)
  )

  yield (api.test('win7_cr')
    + api.properties(
      mastername='client.drmemory',
      buildername='win7-cr',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.step_data("Get the revision number",
      stdout=api.raw_io.output("Dr. Memory version 1.9.16845"
        " -- build 178560794"))
    + api.platform('win', 64)
  )

  yield (api.test('win_8_x64_drm')
    + api.properties(
      mastername='client.drmemory',
      buildername='win-8_x64-drm',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('win', 64)
  )

  yield (api.test('win7_cr_builder')
    + api.properties(
      mastername='client.drmemory',
      buildername='win7-cr-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('win', 64)
  )

  yield (api.test('win7_cr_builder_clobber')
    + api.properties(
      mastername='client.drmemory',
      buildername='win7-cr-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
      clobber='',
    )
    + api.platform('win', 64)
  )

  yield (api.test('win_7_x64_drm')
    + api.properties(
      mastername='client.drmemory',
      buildername='win-7_x64-drm',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('win', 64)
  )

  yield (api.test('mac_builder')
    + api.properties(
      mastername='client.drmemory',
      buildername='mac-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('mac', 64)
  )

  yield (api.test('win_builder')
    + api.properties(
      mastername='client.drmemory',
      buildername='win-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      slavename='TestSlave',
    )
    + api.platform('win', 32)
    + api.step_data("Find package basename",
      stdout=api.raw_io.output("DrMemory-Windows-1.2.3-0x1234567.zip"))
  )

  yield (api.test('builder_not_in_dispatch_directory')
    + api.properties(
      mastername='client.drmemory',
      buildername='nonexistent_builder',
      slavename='TestSlave',
    )
  )
