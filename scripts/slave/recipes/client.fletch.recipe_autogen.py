# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    "depot_tools/bot_update",
    "depot_tools/gclient",
    "recipe_engine/path",
    "recipe_engine/properties",
    "recipe_engine/python",
    "recipe_engine/step",
    "trigger",
]


def target_dartino_linux_debug_arm_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_mac_debug_asan_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def target_dartino_linux_release_arm_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_lk_debug_arm_qemu_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_linux_release_asan_x86_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_mac_release_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def cross_dartino_linux_arm_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
  # trigger step
  trigger_spec = [{"builder_name": "target-dartino-linux-release-arm"},
                  {"builder_name": "target-dartino-linux-debug-arm"}]
  api.trigger(*trigger_spec)


def dartino_mac_release_asan_x86_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def cross_dartino_linux_arm_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
  # trigger step
  trigger_spec = [{"builder_name": "target-dartino-linux-release-arm-dev"},
                  {"builder_name": "target-dartino-linux-debug-arm-dev"}]
  api.trigger(*trigger_spec)


def dartino_free_rtos_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_mac_release_x64_sdk_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def dartino_free_rtos_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_mac_debug_asan_x86_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def dartino_mac_debug_x86_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def target_dartino_linux_debug_arm_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_win_debug_x86_steps(api):
  build_properties = api.properties.legacy()
  # svnkill step; not necessary in recipes
  # update scripts step; implicitly run by recipe engine.
  # extra taskkill step
  api.python("taskkill", api.package_repo_resource("scripts", "slave",
                                                "kill_processes.py"))
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"])
      # dartino annotated steps step
      api.step("annotated steps",
               ["python_slave",
                api.path["checkout"].join("tools", "bots", "dartino.py")],
               allow_subannotations=True,
               env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                    "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"])


def dartino_linux_release_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_mac_debug_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def dartino_linux_release_x64_sdk_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
  # trigger step
  trigger_spec = [{"builder_name": "dartino-mac-release-x64-sdk-dev"}]
  api.trigger(*trigger_spec)


def dartino_linux_debug_asan_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_linux_debug_asan_x86_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_mac_release_asan_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def target_dartino_linux_release_arm_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_mac_release_x86_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def dartino_linux_release_x64_sdk_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
  # trigger step
  trigger_spec = [{"builder_name": "dartino-mac-release-x64-sdk"}]
  api.trigger(*trigger_spec)


def dartino_lk_debug_arm_qemu_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_mac_release_x64_sdk_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={})


def dartino_linux_release_asan_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_linux_debug_x86_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_linux_release_x86_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_linux_debug_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})
      # dartino annotated steps step
      api.python("annotated steps",
                 api.path["checkout"].join("tools", "bots", "dartino.py"),
                 allow_subannotations=True,
                 env={"BUILDBOT_JAVA_HOME": "third_party/java/linux/j2sdk",
                      "BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                      "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"],
                 env={"BUILDBOT_JAVA_HOME": api.path["checkout"].join(
                     "third_party", "java", "linux", "j2sdk")})


def dartino_win_debug_x86_dev_steps(api):
  build_properties = api.properties.legacy()
  # svnkill step; not necessary in recipes
  # update scripts step; implicitly run by recipe engine.
  # extra taskkill step
  api.python("taskkill", api.package_repo_resource("scripts", "slave",
                                                "kill_processes.py"))
  # bot_update step
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = "sdk"
  soln.url = "https://github.com/dartino/sdk.git"
  soln.custom_deps = {}
  soln.custom_vars = {}
  api.gclient.c = src_cfg
  result = api.bot_update.ensure_checkout(no_shallow=True)
  build_properties.update(result.json.output.get("properties", {}))
  # gclient revert step; made unnecessary by bot_update
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {"CHROMIUM_GYP_SYNTAX_CHECK": "1",
         "LANDMINES_VERBOSE": "1",
         "DEPOT_TOOLS_UPDATE": "0"}
  api.python("gclient runhooks wrapper",
             api.package_repo_resource("scripts", "slave", "runhooks_wrapper.py"),
             env=env)
  with api.step.context({'cwd': api.path['checkout']}):
    with api.step.defer_results():
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"])
      # dartino annotated steps step
      api.step("annotated steps",
               ["python_slave",
                api.path["checkout"].join("tools", "bots", "dartino.py")],
               allow_subannotations=True,
               env={"BUILDBOT_ANNOTATED_STEPS_RUN": "1",
                    "BUILDBOT_BUILDERNAME": api.properties["buildername"]})
      # taskkill step
      api.python("Taskkill",
                 api.path["checkout"].join("third_party", "dart", "tools",
                                           "task_kill.py"),
                 args=["--kill_browsers=True"])


dispatch_directory = {
  'target-dartino-linux-debug-arm-dev':
      target_dartino_linux_debug_arm_dev_steps,
  'dartino-mac-debug-asan-x86-dev': dartino_mac_debug_asan_x86_dev_steps,
  'target-dartino-linux-release-arm-dev':
      target_dartino_linux_release_arm_dev_steps,
  'dartino-lk-debug-arm-qemu-dev': dartino_lk_debug_arm_qemu_dev_steps,
  'dartino-linux-release-asan-x86': dartino_linux_release_asan_x86_steps,
  'dartino-mac-release-x86-dev': dartino_mac_release_x86_dev_steps,
  'cross-dartino-linux-arm': cross_dartino_linux_arm_steps,
  'dartino-mac-release-asan-x86': dartino_mac_release_asan_x86_steps,
  'cross-dartino-linux-arm-dev': cross_dartino_linux_arm_dev_steps,
  'dartino-free-rtos': dartino_free_rtos_steps,
  'dartino-mac-release-x64-sdk': dartino_mac_release_x64_sdk_steps,
  'dartino-free-rtos-dev': dartino_free_rtos_dev_steps,
  'dartino-mac-debug-asan-x86': dartino_mac_debug_asan_x86_steps,
  'dartino-mac-debug-x86': dartino_mac_debug_x86_steps,
  'target-dartino-linux-debug-arm': target_dartino_linux_debug_arm_steps,
  'dartino-win-debug-x86': dartino_win_debug_x86_steps,
  'dartino-linux-release-x86-dev': dartino_linux_release_x86_dev_steps,
  'dartino-mac-debug-x86-dev': dartino_mac_debug_x86_dev_steps,
  'dartino-linux-release-x64-sdk-dev': dartino_linux_release_x64_sdk_dev_steps,
  'dartino-linux-debug-asan-x86-dev': dartino_linux_debug_asan_x86_dev_steps,
  'dartino-linux-debug-asan-x86': dartino_linux_debug_asan_x86_steps,
  'dartino-mac-release-asan-x86-dev': dartino_mac_release_asan_x86_dev_steps,
  'target-dartino-linux-release-arm': target_dartino_linux_release_arm_steps,
  'dartino-mac-release-x86': dartino_mac_release_x86_steps,
  'dartino-linux-release-x64-sdk': dartino_linux_release_x64_sdk_steps,
  'dartino-lk-debug-arm-qemu': dartino_lk_debug_arm_qemu_steps,
  'dartino-mac-release-x64-sdk-dev': dartino_mac_release_x64_sdk_dev_steps,
  'dartino-linux-release-asan-x86-dev':
      dartino_linux_release_asan_x86_dev_steps,
  'dartino-linux-debug-x86': dartino_linux_debug_x86_steps,
  'dartino-linux-release-x86': dartino_linux_release_x86_steps,
  'dartino-linux-debug-x86-dev': dartino_linux_debug_x86_dev_steps,
  'dartino-win-debug-x86-dev': dartino_win_debug_x86_dev_steps,
}


def RunSteps(api):
  if api.properties["buildername"] not in dispatch_directory:
    raise api.step.StepFailure("Builder unsupported by recipe.")
  else:
    dispatch_directory[api.properties["buildername"]](api)

def GenTests(api):
  yield (api.test('target_dartino_linux_debug_arm_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='target-dartino-linux-debug-arm-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_debug_asan_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-debug-asan-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('target_dartino_linux_release_arm_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='target-dartino-linux-release-arm-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_lk_debug_arm_qemu_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-lk-debug-arm-qemu-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_release_asan_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-release-asan-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_release_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-release-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('cross_dartino_linux_arm') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='cross-dartino-linux-arm') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_release_asan_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-release-asan-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('cross_dartino_linux_arm_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='cross-dartino-linux-arm-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_free_rtos') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-free-rtos') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_release_x64_sdk') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-release-x64-sdk') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_free_rtos_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-free-rtos-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_debug_asan_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-debug-asan-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_debug_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-debug-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('target_dartino_linux_debug_arm') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='target-dartino-linux-debug-arm') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_win_debug_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-win-debug-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_release_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-release-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_debug_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-debug-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_release_x64_sdk_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-release-x64-sdk-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_debug_asan_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-debug-asan-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_debug_asan_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-debug-asan-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_release_asan_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-release-asan-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('target_dartino_linux_release_arm') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='target-dartino-linux-release-arm') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_release_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-release-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_release_x64_sdk') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-release-x64-sdk') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_lk_debug_arm_qemu') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-lk-debug-arm-qemu') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_mac_release_x64_sdk_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-mac-release-x64-sdk-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_release_asan_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-release-asan-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_debug_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-debug-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_release_x86') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-release-x86') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_linux_debug_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-linux-debug-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('dartino_win_debug_x86_dev') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='dartino-win-debug-x86-dev') +
    api.properties(revision='123456789abcdef') +
    api.properties(bot_id='TestSlave')
        )
  yield (api.test('builder_not_in_dispatch_directory') +
    api.properties(mastername='client.fletch') +
    api.properties(buildername='nonexistent_builder') +
    api.properties(bot_id='TestSlave')
        )
