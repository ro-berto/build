# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'file',
    'depot_tools/gsutil',
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
                        "drmemory/third_party/googletest":
                        "https://github.com/DynamoRIO/googletest.git",
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
                        "drmemory/third_party/googletest":
                        "https://github.com/DynamoRIO/googletest.git",
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


def win_8_x64_drm_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "drmemory/third_party/googletest":
                        "https://github.com/DynamoRIO/googletest.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # clear tools directory step; null converted
    # update tools step; null converted
    # unpack tools step; generic ShellCommand converted
    with api.step.context({
        'cwd': api.path['start_dir'].join('tools', 'buildbot', 'bot_tools'),
        'env': {}}):
      api.step("unpack tools",
               [api.path["start_dir"].join('tools', 'buildbot', 'bot_tools',
                 'unpack.bat')])
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
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools"),
        "CYGWIN": "nodosfilewarning"}}):
      api.step("Build TSan Tests",
               ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat', 'make',
                '-C', api.path["start_dir"].join("tsan", "unittest")])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Prepare to pack test results step; null converted
    # Pack test results step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
                'build_drmemory-rel-64/Testing/Temporary', 'xmlresults'])
    # upload drmemory test logs step
    api.gsutil.upload("testlogs_r" + build_properties["got_revision"] + "_b" +
                      str(api.properties[
                          "buildnumber"]) + ".7z", "chromium-drmemory-builds",
                      "testlogs/from_%s" % api.properties["buildername"])


def win_7_x64_drm_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "drmemory/third_party/googletest":
                        "https://github.com/DynamoRIO/googletest.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # clear tools directory step; null converted
    # update tools step; null converted
    # unpack tools step; generic ShellCommand converted
    with api.step.context({
        'cwd': api.path['start_dir'].join('tools', 'buildbot', 'bot_tools'),
        'env': {}}):
      api.step("unpack tools",
               [api.path["start_dir"].join('tools', 'buildbot', 'bot_tools',
                 'unpack.bat')])
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
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools"),
        "CYGWIN": "nodosfilewarning"}}):
      api.step("Build TSan Tests",
               ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat', 'make',
                '-C', api.path["start_dir"].join("tsan", "unittest")])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Dr. Memory TSan test step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
           '-147'])
    # Prepare to pack test results step; null converted
    # Pack test results step
    with api.step.context({'env': {
        "BOTTOOLS": api.path["start_dir"].join(
            "tools", "buildbot", "bot_tools")}}):
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
                'build_drmemory-rel-64/Testing/Temporary', 'xmlresults'])
    # upload drmemory test logs step
    api.gsutil.upload("testlogs_r" + build_properties["got_revision"] + "_b" +
                      str(api.properties[
                          "buildnumber"]) + ".7z", "chromium-drmemory-builds",
                      "testlogs/from_%s" % api.properties["buildername"])


def win_builder_steps(api):
    build_properties = api.properties.legacy()
    # checkout DrMemory step
    src_cfg = api.gclient.make_config()
    soln = src_cfg.solutions.add()
    soln.name = "drmemory"
    soln.url = "https://github.com/DynamoRIO/drmemory.git"
    soln.custom_deps = {"drmemory/dynamorio":
                        "https://github.com/DynamoRIO/dynamorio.git",
                        "drmemory/third_party/googletest":
                        "https://github.com/DynamoRIO/googletest.git",
                        "tools/buildbot":
                        "https://github.com/DynamoRIO/buildbot.git"}
    api.gclient.c = src_cfg
    result = api.bot_update.ensure_checkout()
    build_properties.update(result.json.output.get("properties", {}))
    # clear tools directory step; null converted
    # update tools step; null converted
    # unpack tools step; generic ShellCommand converted
    with api.step.context({
        'cwd': api.path['start_dir'].join('tools', 'buildbot', 'bot_tools'),
        'env': {}}):
      api.step("unpack tools",
               [api.path["start_dir"].join('tools', 'buildbot', 'bot_tools',
                 'unpack.bat')])
    # get buildnumber step; no longer needed
    with api.step.context({'cwd': api.path['start_dir']}):
      with api.step.context({'env': {
          "BOTTOOLS": api.path["start_dir"].join(
              "tools", "buildbot", "bot_tools")}}):
        # Package dynamorio step
        api.step("Package Dr. Memory",
                 [api.package_repo_resource("scripts", "slave", "drmemory",
                                         "build_env.bat"), 'ctest', '-VV', '-S',
                  str(api.path["checkout"].join("package.cmake")) + ",build=0x" +
                  build_properties["got_revision"][:7] + ";drmem_only"])
      # Find package basename step
      step_result = api.step("Find package basename",
                             ["cmd.exe", "/C", "dir", "/O-D", "/B",
                              "DrMemory-Windows-*0x" + build_properties[
                                  "got_revision"][:7] + ".zip"],
                             stdout=api.raw_io.output_text())
    # There can be multiple if we've done test builds so grab the first
    # line (we sorted by date with /O-D):
    basename = step_result.stdout.split()[0][:-4]
    # Delete prior sfx archive step
    api.file.remove("Delete prior sfx archive",
        api.path["start_dir"].join(basename + "-sfx.exe"),
        ok_ret=(0,1))
    # Create sfx archive step
    lastdir = api.path.basename(api.path["start_dir"])
    with api.step.context({
        'cwd': api.path['start_dir'],
        'env': {
            "BOTTOOLS": api.path["start_dir"].join(
                "tools", "buildbot", "bot_tools")
        }}):
      api.step("create sfx archive",
               [api.package_repo_resource("scripts", "slave", "drmemory",
                                       "build_env.bat"), "7z", "a", "-sfx",
                basename + "-sfx.exe",
                # To get the archive to contain paths relative to the
                # ...\\ZIP\\basename\\ dir we pass ..\\lastdir:
                api.path.join(
                  '..', lastdir, 'build_drmemory-debug-32', '_CPack_Packages',
                  'Windows', 'ZIP', basename, '*')])
    # upload latest build step
    api.file.copy("copy locally",
        api.path["start_dir"].join(basename + "-sfx.exe"),
        api.path["start_dir"].join("drmemory-windows-latest-sfx.exe"))
    with api.step.context({'cwd': api.path['start_dir']}):
      api.gsutil.upload("drmemory-windows-latest-sfx.exe",
                        "chromium-drmemory-builds",
                        "")
    # upload drmemory build step
    api.gsutil.upload("DrMemory-Windows-*" + build_properties["got_revision"][
                      :7] + ".zip", "chromium-drmemory-builds", "builds/")


dispatch_directory = {
    'linux-builder': linux_builder_steps,
    'linux-lucid_x64-drm': linux_lucid_x64_drm_steps,
    'win-8_x64-drm': win_8_x64_drm_steps,
    'win-7_x64-drm': win_7_x64_drm_steps,
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
       bot_id='TestSlave',
     )
  )

  yield (api.test('linux_lucid_x64_drm')
    + api.properties(
      mastername='client.drmemory',
      buildername='linux-lucid_x64-drm',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      bot_id='TestSlave',
    )
    + api.platform('linux', 64)
  )

  yield (api.test('win_8_x64_drm')
    + api.properties(
      mastername='client.drmemory',
      buildername='win-8_x64-drm',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      bot_id='TestSlave',
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
      bot_id='TestSlave',
    )
    + api.platform('win', 64)
  )

  yield (api.test('win_builder')
    + api.properties(
      mastername='client.drmemory',
      buildername='win-builder',
      revision='123456789abcdef',
      got_revision='123456789abcdef',
      buildnumber=42,
      bot_id='TestSlave',
    )
    + api.platform('win', 32)
    + api.step_data("Find package basename",
      stdout=api.raw_io.output_text("DrMemory-Windows-1.2.3-0x1234567.zip"))
  )

  yield (api.test('builder_not_in_dispatch_directory')
    + api.properties(
      mastername='client.drmemory',
      buildername='nonexistent_builder',
      bot_id='TestSlave',
    )
  )
