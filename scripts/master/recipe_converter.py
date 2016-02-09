# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import master.chromium_step
import master.log_parser.retcode_command
import master.factory.commands
import master.factory.drmemory_factory
import master.master_utils
import buildbot.process.properties
import buildbot.steps.transfer
import buildbot.steps.shell
import buildbot.steps.trigger
import sys
import collections
import cStringIO
import pprint
import buildbot
import logging
import datetime

# Terrible hack; to enable converting triggers.
_GLOBAL_BUILDMASTER_CONFIG = None

_master_builder_map = {
    'Chromium GPU': ['Android Debug (Nexus 5)',
                     'Android Debug (Nexus 6)',
                     'Android Debug (Nexus 9)',
                    ],
    'Chromium ChromeDriver': ['Win7',
                              'Linux',
                              'Linux32',
                              'Mac 10.6',
                             ],
    'Chromium GPU FYI': ['Win7 Audio',
                         'Linux Audio',
                        ],
    'DynamoRIO': ['win-xp-dr',
                  'win-7-dr',
                  'win-8-dr',
                  'linux-dr',
                  'linux-dr-package',
                  'win-dr-package',
                  'win-xp-dr-nightly',
                  'win-7-dr-nightly',
                  'win-8-dr-nightly',
                  'linux-dr-nightly',
                  ],
    'Dart': ['cross-dartino-linux-arm',
             'dartino-linux-release-x86',
             'dartino-linux-debug-x86',
             'dartino-linux-release-asan-x86',
             'dartino-linux-debug-asan-x86',
             'target-dartino-linux-release-arm',
             'target-dartino-linux-debug-arm',
             'dartino-win-debug-x86',
             'dartino-mac-release-x86',
             'dartino-mac-debug-x86',
             'dartino-mac-release-asan-x86',
             'dartino-mac-debug-asan-x86',
             'dartino-free-rtos',
             'dartino-lk-debug-arm-qemu',
             'dartino-linux-release-x64-sdk',
             'dartino-mac-release-x64-sdk',
             'dartino-linux-release-x86-dev',
             'dartino-linux-debug-x86-dev',
             'dartino-linux-release-asan-x86-dev',
             'dartino-linux-debug-asan-x86-dev',
             'cross-dartino-linux-arm-dev',
             'target-dartino-linux-release-arm-dev',
             'target-dartino-linux-debug-arm-dev',
             'dartino-win-debug-x86-dev',
             'dartino-mac-release-x86-dev',
             'dartino-mac-debug-x86-dev',
             'dartino-mac-release-asan-x86-dev',
             'dartino-mac-debug-asan-x86-dev',
             'dartino-free-rtos-dev',
             'dartino-lk-debug-arm-qemu-dev',
             'dartino-linux-release-x64-sdk-dev',
             'dartino-mac-release-x64-sdk-dev',
            ]
}

_master_name_map = {
    'Chromium GPU': 'chromium.gpu',
    'Chromium ChromeDriver': 'chromium.chromedriver',
    'Chromium GPU FYI': 'chromium.gpu.fyi',
    'DynamoRIO': 'client.dynamorio',
    'Dart': 'client.fletch',
}

# Used like a structure.
class recipe_chunk(object):
  def __init__(self):
    self.deps = set()
    self.steps = list()
    self.tests = set()

  def __repr__(self):
    return pprint.pformat(self.deps, indent=4) + '\n' + \
        pprint.pformat(self.steps, indent=4)

  # Note that addition is *not* commutative; rc1 + rc2 implies that rc1 will be
  # executed first.
  def __add__(self, other):
    s = recipe_chunk()
    s.deps = self.deps | other.deps
    s.tests = self.tests | other.tests
    s.steps = self.steps + other.steps
    return s

_step_signatures = {
  'update_scripts': (buildbot.steps.shell.ShellCommand,
                     {
                       'command': ['gclient', 'sync', '--verbose', '--force'],
                       'description': 'update_scripts',
                       'name': 'update_scripts',
                       'workdir': '../../..'
                     }
                    ),
  'bot_update': (master.chromium_step.AnnotatedCommand,
                 {
                   'command': ['python', '-u',
                               '../../../scripts/slave/bot_update.py'],
                   'description': 'bot_update',
                   'name': 'bot_update',
                   'workdir': 'build',
                 }
                ),
  'win_bot_update': (master.chromium_step.AnnotatedCommand,
                 {
                   'command': ['python', '-u',
                               '..\\..\\..\\scripts\\slave\\bot_update.py'],
                   'description': 'bot_update',
                   'name': 'bot_update',
                   'workdir': 'build',
                 }
                ),
  'cleanup_temp': (master.log_parser.retcode_command.ReturnCodeCommand,
                   {
                     'command': ['python',
                                 '../../../scripts/slave/cleanup_temp.py'],
                     'description': 'cleanup_temp',
                     'name': 'cleanup_temp',
                   }
                  ),
  'win_cleanup_temp': (master.log_parser.retcode_command.ReturnCodeCommand,
      {
        'command': ['python',
                    '..\\..\\..\\scripts\\slave\\cleanup_temp.py'],
        'description': 'cleanup_temp',
        'name': 'cleanup_temp',
      }
    ),
  'gclient_update':      (master.chromium_step.GClient,
                          {
                            'mode': 'update',
                          }),
  'gclient_safe_revert': (buildbot.steps.shell.ShellCommand,
                          {
                            'command': ['python',
                              '../../../scripts/slave/gclient_safe_revert.py',
                              '.', 'gclient'],
                            'description': 'gclient_revert',
                            'name': 'gclient_revert',
                            'workdir': 'build',
                          }
    ),
  'win_gclient_safe_revert': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['python_slave',
          '..\\..\\..\\scripts\\slave\\gclient_safe_revert.py',
          '.', 'gclient.bat'],
        'description': 'gclient_revert',
        'name': 'gclient_revert',
        'workdir': 'build',
      }
    ),
  'bb_run_bot':   (master.chromium_step.AnnotatedCommand,
                   {
                     'command': ['python',
                       'src/build/android/buildbot/bb_run_bot.py'],
                     'name': 'slave_steps',
                     'description': 'slave_steps',
                   }
                  ),
  'gclient_runhooks_wrapper': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['python', '../../../scripts/slave/runhooks_wrapper.py'],
        'description': 'gclient hooks',
        'env': {},
        'name': 'runhooks'
        # NOTE: locking shouldn't be required, as only one recipe is ever run on
        # a slave at a time; specifically, a SlaveLock of type slave_exclusive
        # *should be* redundant. Noted here in case it isn't. (aneeshm)
      }
    ),
  'win_gclient_runhooks_wrapper': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['python_slave',
                    '..\\..\\..\\scripts\\slave\\runhooks_wrapper.py'],
        'description': 'gclient hooks',
        'env': {},
        'name': 'runhooks'
        # NOTE: locking shouldn't be required, as only one recipe is ever run on
        # a slave at a time; specifically, a SlaveLock of type slave_exclusive
        # *should be* redundant. Noted here in case it isn't. (aneeshm)
      }
    ),
  'chromedriver_buildbot_run': (master.chromium_step.AnnotatedCommand,
      {
        'name': 'annotated_steps',
        'description': 'annotated_steps',
        'command': ['python',
          '../../../scripts/slave/chromium/chromedriver_buildbot_run.py'],
      }
    ),
  'win_chromedriver_buildbot_run': (master.chromium_step.AnnotatedCommand,
      {
        'name': 'annotated_steps',
        'description': 'annotated_steps',
        'command': ['python_slave',
          '..\\..\\..\\scripts\\slave\\chromium\\chromedriver_buildbot_run.py'],
      }
    ),
  'compile_py':
    (master.factory.commands.CompileWithRequiredSwarmTargets,
      {
        'command': ['python', '../../../scripts/slave/compile.py'],
        'name': 'compile',
        'description': 'compiling',
        'descriptionDone': 'compile',
      }
    ),
  'win_compile_py':
    (master.factory.commands.CompileWithRequiredSwarmTargets,
      {
        'command': ['python_slave', '..\\..\\..\\scripts\\slave\\compile.py'],
        'name': 'compile',
        'description': 'compiling',
        'descriptionDone': 'compile',
      }
    ),
  'win_svnkill': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['%WINDIR%\\system32\\taskkill', '/f', '/im', 'svn.exe',
                    '||', 'set', 'ERRORLEVEL=0'],
        'description': 'svnkill',
        'name': 'svnkill',
      }
    ),
  'win_update_scripts': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['gclient.bat', 'sync', '--verbose', '--force'],
        'description': 'update_scripts',
        'name': 'update_scripts',
      }
    ),
  'win_taskkill': (master.log_parser.retcode_command.ReturnCodeCommand,
      {
        'command': ['python', '..\\..\\..\\scripts\\slave\\kill_processes.py'],
        'name': 'taskkill',
        'description': 'taskkill',
      }
    ),
  'runtest': (master.chromium_step.AnnotatedCommand,
      {
        'command': ['python', '../../../scripts/slave/runtest.py'],
      }
    ),
  'win_runtest': (master.chromium_step.AnnotatedCommand,
      {
        'command': ['python_slave', '..\\..\\..\\scripts\\slave\\runtest.py'],
      }
    ),
  'clear_tools': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['rd', '/q', '/s', 'buildbot'],
        'name': 'clear tools directory',
        'workdir': 'tools',
      }
    ),
  'checkout_dynamorio': (buildbot.steps.source.Git,
      {
        'branch': 'master',
        'name': 'Checkout DynamoRIO',
        'workdir': 'dynamorio',
        'repourl': 'https://github.com/DynamoRIO/dynamorio.git',
      }
    ),
  'checkout_dynamorio_tools': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['git', 'clone',
          'https://github.com/DynamoRIO/buildbot.git'],
        'name': 'update tools',
        'workdir': 'tools',
      }
    ),
  'dynamorio_unpack_tools': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['unpack.bat'],
        'name': 'unpack tools',
        'description': 'unpack tools',
        'workdir': 'tools/buildbot/bot_tools',
      }
    ),
  'win_dynamorio_nightly_suite': (master.factory.drmemory_factory.CTest,
      {
        'command': ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat',
          'ctest', '--timeout', '120', '-VV', '-S'],
        'name': 'nightly suite',
        'descriptionDone': 'nightly suite',
      }
    ),
  'dynamorio_nightly_suite': (master.factory.drmemory_factory.CTest,
      {
        'command': ['ctest', '--timeout', '120', '-VV', '-S',
          '../dynamorio/suite/runsuite.cmake,nightly;long;'+\
              'site=X64.Linux.VS2010.BuildBot'],
        'descriptionDone': 'nightly suite',
        'name': 'nightly suite',
      }
    ),
  'win_dynamorio_precommit':(master.factory.drmemory_factory.CTest,
      {
        'command': ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat',
          'ctest', '--timeout', '120', '-VV', '-S',
          '../dynamorio/suite/runsuite.cmake'],
        'descriptionDone': 'pre-commit suite',
        'name': 'pre-commit suite',
      }
    ),
  'dynamorio_precommit': (master.factory.drmemory_factory.CTest,
      {
        'command': ['ctest', '--timeout', '120', '-VV', '-S',
          '../dynamorio/suite/runsuite.cmake'],
        'name': 'pre-commit suite',
        'descriptionDone': 'pre-commit suite',
      }
    ),
  'upload_dynamorio_docs': (buildbot.steps.transfer.DirectoryUpload,
      {
        'blocksize': 16384,
        'masterdest': 'public_html/dr_docs',
        'slavesrc': 'install/docs/html',
        'workdir': 'build',
      }
    ),
  'get_dynamorio_buildnumber': (buildbot.steps.shell.SetProperty,
      {
        'description': 'get package build number',
        'name': 'get package build number',
      }
    ),
  'package_dynamorio': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['ctest', '-VV', '-S'],
        'description': 'Package DynamoRIO',
        'name': 'Package DynamoRIO',
      }
    ),
  'find_dynamorio_package': (buildbot.steps.shell.SetProperty,
      {
        'description': 'find package file',
        'name': 'find package file',
        'strip': True,
      }
    ),
  'upload_dynamorio_package': (buildbot.steps.transfer.FileUpload,
      {
        'blocksize': 16384,
        'name': 'Upload DR package',
      }
    ),
  'win_package_dynamorio': (buildbot.steps.shell.ShellCommand,
      {
        'command': ['E:\\b\\build\\scripts\\slave\\drmemory\\build_env.bat',
          'ctest', '-VV', '-S'],
        'description': 'Package DynamoRIO',
        'name': 'Package DynamoRIO',
      }
    ),
  'dartino': (master.chromium_step.AnnotatedCommand,
      {
        'command': ['python', 'tools/bots/dartino.py'],
        'description': 'annotated_steps',
        'env': {'BUILDBOT_ANNOTATED_STEPS_RUN': '1'},
        'name': 'annotated_steps',
        'workdir': 'build/sdk',
      }
    ),
  'dart_taskkill': (buildbot.steps.shell.ShellCommand,
      {
        'command': 'python third_party/dart/tools/task_kill.py'+\
            ' --kill_browsers=True',
        'name': 'Taskkill',
        'workdir': 'build/sdk',
      }
    ),
  'trigger': (buildbot.steps.trigger.Trigger,
      {
        # nothing here for now
      }
    ),
  'win_dart_taskkill': (buildbot.steps.shell.ShellCommand,
      {
        'command': 'python third_party/dart/tools/task_kill.py'+\
            ' --kill_browsers=True',
        'name': 'Taskkill',
        'workdir': 'build\\sdk',
      }
    ),
  'win_dartino': (master.chromium_step.AnnotatedCommand,
      {
        'command': ['python_slave', 'tools/bots/dartino.py'],
        'description': 'annotated_steps',
        'env': {'BUILDBOT_ANNOTATED_STEPS_RUN': '1'},
        'name': 'annotated_steps',
        'workdir': 'build\\sdk',
      }
    ),
}

# Conversion functions for specific step types.

# Convert special arguments to recipes.
def convert_arguments(args):
  arg_lookup = {
      '--build-number': ("'%s', %s", '--build-number',
                         'api.properties["buildnumber"]'),
      '--builder-name': ("'%s', %s", '--builder-name',
                         'api.properties["buildername"]'),

  }
  fmtstr = ''
  fmtlist = []
  for arg in args:
    if isinstance(arg, str):
      if arg in arg_lookup:
        fmtstr = fmtstr + ', ' + arg_lookup[arg][0]
        fmtlist = fmtlist + list(arg_lookup[arg][1:])
      else:
        fmtstr = fmtstr + ", '%s'"
        fmtlist = fmtlist + [arg]
    if isinstance(arg, buildbot.process.properties.WithProperties):
      if arg.fmtstring == '--build-properties=%s':
        fmtstr = fmtstr + ', ' + '"--build-properties=%%s" %% %s'
        fmtlist = fmtlist +\
            ["api.json.dumps(build_properties, separators=(',', ':'))"]

  return fmtstr[2:] % tuple(fmtlist)

# Helpers for converting trigger steps
def get_builders_from_triggerable(c, sched_name):
  for sched in c['schedulers']:
    if sched.name == sched_name:
      return sched.builderNames
  raise Exception('Triggerable %s not found' % sched_name)

def builders_to_triggerspec(builder_list):
  return [{'builder_name': x} for x in builder_list]

def sched_to_triggerspec(sched_name):
  return builders_to_triggerspec(\
      get_builders_from_triggerable(_GLOBAL_BUILDMASTER_CONFIG, sched_name))

# Converter for use when step a step is unmatched or multiply matched.
def dump_converter(step, comment):
  rc = recipe_chunk()
  rc.steps.append('# %s' % comment)
  rc.steps.append(pprint.pformat(step, indent=2))
  return rc

def trigger_converter(step):
  rc = recipe_chunk()
  rc.deps.add('trigger')
  trigger_spec = []
  for sched in step[1]['schedulerNames']:
    trigger_spec.extend(sched_to_triggerspec(sched))
  rc.steps.append('# trigger step')
  rc.steps.append('trigger_spec = %s' % repr(trigger_spec))
  rc.steps.append('api.trigger(*trigger_spec)')
  return rc

def dart_taskkill_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/path')
  env = {}
  if 'BUILDBOT_JAVA_HOME' in step[1]['env']:
    env = "{'BUILDBOT_JAVA_HOME': api.path['checkout'].join('third_party', "+\
        "'java', 'linux', 'j2sdk')}"
  rc.steps.append("# taskkill step")
  rc.steps.append('api.python("Taskkill", '+\
      'api.path["checkout"].join("third_party", "dart", "tools", '+\
      '"task_kill.py"), args=["--kill_browsers=True"], '+\
      'env=%s, ' % env +\
      'cwd=api.path["checkout"])')
  return rc

def win_dart_taskkill_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/path')
  rc.steps.append("# taskkill step")
  rc.steps.append('api.python("Taskkill", '+\
      'api.path["checkout"].join("third_party", "dart", "tools", '+\
      '"task_kill.py"), args=["--kill_browsers=True"], '+\
      'cwd=api.path["checkout"])')
  return rc

def dartino_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/path')
  rc.deps.add('recipe_engine/properties')
  rc.steps.append("# dartino annotated steps step")
  env_add = ', "BUILDBOT_BUILDERNAME": api.properties["buildername"]'
  rc.steps.append('api.python("annotated steps", '+\
      'api.path["checkout"].join("tools", "bots", "dartino.py"), '+\
      'allow_subannotations=True, env={%s%s}, ' % (repr(step[1]['env'])[1:-1],
        env_add) +\
      'cwd=api.path["checkout"])')
  return rc

def win_dartino_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/step')
  rc.deps.add('recipe_engine/path')
  rc.steps.append("# dartino annotated steps step")
  env_add = ', "BUILDBOT_BUILDERNAME": api.properties["buildername"]'
  rc.steps.append('api.step("annotated steps", ["python_slave", '+\
      'api.path["checkout"].join("tools", "bots", "dartino.py")], '+\
      'allow_subannotations=True, env={%s%s}, ' % (repr(step[1]['env'])[1:-1],
        env_add) +\
      'cwd=api.path["checkout"])')
  return rc

def win_package_dynamorio_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/step')
  rc.deps.add('recipe_engine/path')
  rc.deps.add('recipe_engine/properties')
  rc.steps.append('# Package DynamoRIO step')
  build_env_bat = 'api.path["build"].join("scripts", "slave", "drmemory", '+\
      '"build_env.bat")'
  confstr = 'str(api.path["checkout"].join("make", "package.cmake")) + '+\
      '",build=0x" + str(api.properties["revision"])[:7]'
  env = '{"BOTTOOLS": api.path["slave_build"].join("tools", "buildbot", '+\
      '"bot_tools")}'
  rc.steps.append('api.step("Package DynamoRIO", '+\
      '[%s, "ctest", "-VV", "-S", %s], env=%s)' % (build_env_bat, confstr, env))
  return rc

def dynamorio_nightly_suite_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/step')
  rc.deps.add('recipe_engine/path')
  rc.steps.append('# dynamorio nightly suite step')
  rc.steps.append('api.step("nightly suite", ["ctest", "--timeout", "120", '+\
      '"-VV", "-S", str(api.path["checkout"].join("suite", "runsuite.cmake"))'+\
      ' + ",nightly;long;site=X64.Linux.VS2010.BuildBot"])')
  return rc

def find_dynamorio_package_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# find package file step; no longer necessary')
  return rc

def upload_dynamorio_package_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/properties')
  rc.deps.add('gsutil')
  rc.steps.append('# upload dynamorio package')
  local_file = '"DynamoRIO-Linux-*" + str(api.properties["revision"])[:7]'+\
      ' + ".tar.gz"'
  bucket = 'chromium-dynamorio'
  remote_dir = '"builds/"'
  rc.steps.append('api.gsutil.upload(%s, "%s", %s)' % (local_file, bucket,
    remote_dir))
  local_file = '"DynamoRIO-Windows-*" + str(api.properties["revision"])'+\
      '[:7] + ".zip"'
  rc.steps.append('api.gsutil.upload(%s, "%s", %s)' % (local_file, bucket,
    remote_dir))
  return rc

def package_dynamorio_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/step')
  rc.deps.add('recipe_engine/path')
  rc.deps.add('recipe_engine/properties')
  rc.steps.append('# Package DynamoRIO step')
  confstr = 'str(api.path["checkout"].join("make", "package.cmake")) + '+\
      '",build=0x" + build_properties["revision"][:7]'
  rc.steps.append('api.step("Package DynamoRIO", ["ctest", "-VV", "-S", %s])' %\
      confstr)
  return rc

def get_dynamorio_buildnumber_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# get buildnumber step; no longer needed')
  return rc

def upload_dynamorio_docs_converter(step):
  rc = recipe_chunk()
  rc.deps.add('gsutil')
  rc.deps.add('recipe_engine/path')
  local_file = 'api.path["slave_build"].join("install", "docs", "html")'
  bucket = '"chromium-dynamorio"'
  remote_dir = '"dr_docs/"'
  args = ['-r', '-m']
  rc.steps.append("# upload dynamorio docs step")
  rc.steps.append('api.gsutil.upload(%s, %s, %s, "%s")' % (local_file,
    bucket, remote_dir, repr(args)))
  return rc

def dynamorio_precommit_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/step')
  rc.deps.add('recipe_engine/path')
  rc.steps.append('# pre-commit suite step')
  command = repr(step[1]['command'][:-1])[1:-1]
  cmake_file = 'api.path["checkout"].join("suite", "runsuite.cmake")'
  cwd = 'api.path["slave_build"]'
  rc.steps.append('api.step("pre-commit suite", '+\
      '[%s, %s], cwd=%s, ok_ret="all")' % (command, cmake_file, cwd))
  return rc

def win_dynamorio_precommit_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/step')
  rc.deps.add('recipe_engine/path')
  rc.steps.append('# build_env step')
  fmtstr = 'api.step("pre-commit suite", [%s, %s, %s],  env=%s, '+\
      'cwd=api.path["slave_build"])'
  command = 'api.path["build"].join("scripts", "slave", "drmemory", '+\
      '"build_env.bat")'
  args = step[1]['command'][1:-1]
  runsuite = 'api.path["checkout"].join("suite", "runsuite.cmake")'
  env = '{"BOTTOOLS": api.path["slave_build"].join("tools", "buildbot", '+\
      '"bot_tools")}'
  rc.steps.append(fmtstr % (command, repr(args)[1:-1], runsuite, env))
  return rc

def win_dynamorio_nightly_suite_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/step')
  rc.steps.append('# dynamorio win nightly suite step')
  fmtstr = 'api.step("%s", [%s, %s], env=%s, cwd=api.path["slave_build"])'
  env = '{"BOTTOOLS": '+\
      'api.path["slave_build"].join("tools", "buildbot", "bot_tools")}'
  command = 'api.path["build"].join("scripts", "slave", "drmemory", '+\
      '"build_env.bat")'
  step[1]['command'][-1] = step[1]['command'][-1][3:]
  command_args = repr(step[1]['command'][1:])[1:-1]
  rc.steps.append(fmtstr % (step[1]['name'], command, command_args, env))
  return rc

def checkout_dynamorio_converter(step):
  rc = recipe_chunk()
  rc.deps.add('depot_tools/bot_update')
  rc.deps.add('depot_tools/gclient')
  rc.steps.append('# checkout DynamiRIO step')
  rc.steps.append('src_cfg = api.gclient.make_config(GIT_MODE=True)')
  rc.steps.append('soln = src_cfg.solutions.add()')
  rc.steps.append('soln.name = "%s"' % 'dynamorio')
  rc.steps.append('soln.url = "%s"' % step[1]['repourl'])
  rc.steps.append('api.gclient.c = src_cfg')
  rc.steps.append('result = api.bot_update.ensure_checkout(force=True)')
  rc.steps.append(
      'build_properties.update(result.json.output.get("properties", {}))')
  return rc

def generic_shellcommand_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/step')
  fmtstr = 'api.step("%s", %s, env=%s, cwd=%s)'
  cwd = 'api.path["slave_build"]'
  if step[1].get('workdir', ''):
    cwd += '.join(%s)' % repr(step[1]['workdir'].split('/'))[1:-1]
  env = "{}"
  if step[1].get('env', {}):
    env = repr(step[1]['env'])
  rc.steps.append('# %s step; generic ShellCommand converted' % step[1]['name'])
  rc.steps.append(fmtstr % (step[1]['name'], repr(step[1]['command']), env,
    cwd))
  return rc

def runtest_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/path')
  rc.deps.add('recipe_engine/json')
  rc.steps.append('# runtest step')
  fmtstr = 'api.python("%s", api.path["build"].join("scripts", "slave",'+\
      '"runtest.py"), args=[%s])'
  rc.steps.append(fmtstr % (step[1]['name'],
    convert_arguments(step[1]['command'].items[2:])))
  return rc

def win_runtest_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/path')
  rc.steps.append('# runtest step')
  fmtstr = 'api.step("%s", ["python_slave", '+\
      'api.path["build"].join("scripts", "slave", "runtest.py"), %s])'
  rc.steps.append(fmtstr % (step[1]['name'],
    convert_arguments(step[1]['command'].items[2:])))
  return rc

def win_taskkill_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/path')
  rc.steps.append('# taskkill step')
  rc.steps.append('api.python("taskkill", api.path["build"].join("scripts", '+\
      '"slave", "kill_processes.py"))')
  return rc

def win_svnkill_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# svnkill step; not necessary in recipes')
  return rc

def cleanup_temp_converter(step):
  rc = recipe_chunk()
  rc.deps.add('chromium')
  rc.steps.append('# cleanup_temp step')
  rc.steps.append('api.chromium.cleanup_temp()')
  return rc

# Converter for update_scripts; the recipe engine does this automatically, so
# this converter is a no-op.
def update_scripts_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# update scripts step; implicitly run by recipe engine.')
  return rc

# NOTE: may require support for kwargs later.
def gclient_safe_revert_converter(step):
  rc = recipe_chunk()
  # This *should be* a no-op if run after bot_update; and bot_update has been
  # found to have been run on all builders encountered/attempted to be converted
  # so far.
  rc.steps.append('# gclient revert step; made unnecessary by bot_update')
  return rc

def gclient_update_converter(step):
  rc = recipe_chunk()
  # This *should be* a no-op if run after bot_update; and bot_update has been
  # found to have been run on all builders encountered/attempted to be converted
  # so far.
  rc.steps.append('# gclient update step; made unnecessary by bot_update')
  return rc

def bot_update_converter(step):
  rc = recipe_chunk()
  rc.deps = {'depot_tools/gclient', 'depot_tools/bot_update'}
  rc.steps.append('# bot_update step')
  # First, get the gclient config out of the command
  gclient_config = {}
  exec(step[1]['command'][4], gclient_config)
  # Write the gclient config to the recipe.
  rc.steps.append('src_cfg = api.gclient.make_config(GIT_MODE=True)')
  for soln in gclient_config['solutions']:
    rc.steps.append('soln = src_cfg.solutions.add()')
    rc.steps.append('soln.name = "%s"' % soln['name'])
    rc.steps.append('soln.url = "%s"' % soln['url'])
    if 'custom_deps' in soln:
      rc.steps.append('soln.custom_deps = %s' % repr(soln['custom_deps']))
    if 'custom_vars' in soln:
      rc.steps.append('soln.custom_vars = %s' % repr(soln['custom_vars']))
  if 'target_os' in gclient_config:
    rc.steps.append('src_cfg.target_os = set(%s)' %
        repr(gclient_config['target_os']))
  # If there's a revision mapping, get that as well.
  for rm in step[1]['command']:
    if isinstance(rm, basestring) and rm.startswith('--revision_mapping='):
      exec(rm[2:], gclient_config)
      break # There really shouldn't be more than a single revision mapping.
  if 'revision_mapping' in gclient_config:
    rc.steps.append('src_cfg.got_revision_mapping.update(%s)' %
        gclient_config['revision_mapping'])
  rc.steps.append('api.gclient.c = src_cfg')
  # Then, call bot_update on it.
  rc.steps.append('result = api.bot_update.ensure_checkout(force=True)')
  rc.steps.append(
      'build_properties.update(result.json.output.get("properties", {}))')
  # NOTE: wherever there is a gclient_runhooks steps after bot_update (which
  # *should* be everywhere), the '--gyp_env' argument need not be passed in;
  # that is why it is ignored here. (aneeshm)
  return rc

def bb_run_bot_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# slave_steps step')
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/json')
  build_properties = "'--build-properties=%s' % " +\
      "api.json.dumps(build_properties, separators=(',', ':'))"
  fmtstr = 'api.python("slave_steps", "%s", args=[%s, \'%s\'],' +\
      ' allow_subannotations=True)'
  rc.steps.append(fmtstr % (step[1]['command'][1], build_properties,
                            step[1]['command'][3]))
  return rc

def gclient_runhooks_wrapper_converter(step):
  rc = recipe_chunk()
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/path')
  rc.steps.append('# gclient runhooks wrapper step')
  rc.steps.append('env = %s' % repr(step[1]['env']))
  rc.steps.append('api.python("gclient runhooks wrapper", ' +\
      'api.path["build"].join("scripts", "slave", "runhooks_wrapper.py"), '+\
      'env=env)')
  return rc

def chromedriver_buildbot_run_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# annotated_steps step')
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/json')
  build_properties = "'--build-properties=%s' % " +\
      "api.json.dumps(build_properties, separators=(',', ':'))"
  cdbbrun_command = 'api.path["build"].join("scripts", "slave", "chromium", '+\
      '"chromedriver_buildbot_run.py")'
  fmtstr = 'api.python("annotated_steps", %s, args=[%s, \'%s\'],' +\
      ' allow_subannotations=True)'
  rc.steps.append(fmtstr % (cdbbrun_command, build_properties,
                            step[1]['command'][3]))
  return rc

def win_chromedriver_buildbot_run_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# annotated_steps step')
  rc.deps.add('recipe_engine/step')
  rc.deps.add('recipe_engine/json')
  build_properties = "'--build-properties=%s' % " +\
      "api.json.dumps(build_properties, separators=(',', ':'))"
  cdbbrun_command = 'api.path["build"].join("scripts", "slave", "chromium", '+\
      '"chromedriver_buildbot_run.py")'
  fmtstr = 'api.step("annotated_steps", ["python_slave", %s, %s, \'%s\'],' +\
      ' allow_subannotations=True)'
  rc.steps.append(fmtstr % (cdbbrun_command, build_properties,
                            step[1]['command'][3]))
  return rc

def compile_py_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# compile.py step')
  rc.deps.add('recipe_engine/python')
  rc.deps.add('recipe_engine/path')
  rc.deps.add('recipe_engine/properties')
  fmtstr = 'api.python("compile", %s, args=args)'
  compile_command = 'api.path["build"].join("scripts", "slave", "compile.py")'
  args = [x for x in step[1]['command'].items[2:] if isinstance(x, str)]
  rc.steps.append('args = %s' % repr(args))
  for x in step[1]['command'].items[2:]:
    if isinstance(x, buildbot.process.properties.WithProperties) and\
       x.fmtstring == '%s' and\
       x.args == ('clobber:+--clobber',):
      rc.steps.append('if api.properties.get("clobber"):')
      rc.steps.append(['args.append("--clobber")'])
  rc.steps.append(fmtstr % compile_command)
  return rc

def win_compile_py_converter(step):
  rc = recipe_chunk()
  rc.steps.append('# compile.py step')
  rc.deps.add('recipe_engine/path')
  fmtstr = 'api.step("compile", ["%s", %s] + args)'
  compile_command = 'api.path["build"].join("scripts", "slave", "compile.py")'
  args = [x for x in step[1]['command'].items[2:] if isinstance(x, str)]
  rc.steps.append('args = %s' % repr(args))
  for x in step[1]['command'].items[2:]:
    if isinstance(x, buildbot.process.properties.WithProperties) and\
       x.fmtstring == '%s' and\
       x.args == ('clobber:+--clobber',):
      rc.steps.append('if api.properties.get("clobber"):')
      rc.steps.append(['args.append("--clobber")'])
  rc.steps.append(fmtstr % ('python_slave', compile_command))
  return rc

_step_converters_map = {
    'cleanup_temp': cleanup_temp_converter,
    'win_cleanup_temp': cleanup_temp_converter,
    'update_scripts': update_scripts_converter,
    'gclient_safe_revert': gclient_safe_revert_converter,
    'win_gclient_safe_revert': gclient_safe_revert_converter,
    'gclient_update': gclient_update_converter,
    'bot_update': bot_update_converter,
    'win_bot_update': bot_update_converter,
    'bb_run_bot': bb_run_bot_converter,
    'gclient_runhooks_wrapper': gclient_runhooks_wrapper_converter,
    'win_gclient_runhooks_wrapper': gclient_runhooks_wrapper_converter,
    'chromedriver_buildbot_run': chromedriver_buildbot_run_converter,
    'win_chromedriver_buildbot_run': win_chromedriver_buildbot_run_converter,
    'compile_py': compile_py_converter,
    'win_compile_py': win_compile_py_converter,
    'win_svnkill': win_svnkill_converter,
    'win_update_scripts': update_scripts_converter,
    'win_taskkill': win_taskkill_converter,
    'runtest': runtest_converter,
    'win_runtest': win_runtest_converter,
    'clear_tools': generic_shellcommand_converter,
    'checkout_dynamorio': checkout_dynamorio_converter,
    'checkout_dynamorio_tools': generic_shellcommand_converter,
    'dynamorio_unpack_tools': generic_shellcommand_converter,
    'win_dynamorio_nightly_suite': win_dynamorio_nightly_suite_converter,
    'win_dynamorio_precommit': win_dynamorio_precommit_converter,
    'dynamorio_precommit': dynamorio_precommit_converter,
    'upload_dynamorio_docs': upload_dynamorio_docs_converter,
    'get_dynamorio_buildnumber': get_dynamorio_buildnumber_converter,
    'package_dynamorio': package_dynamorio_converter,
    'find_dynamorio_package': find_dynamorio_package_converter,
    'upload_dynamorio_package': upload_dynamorio_package_converter,
    'dynamorio_nightly_suite': dynamorio_nightly_suite_converter,
    'win_package_dynamorio': win_package_dynamorio_converter,
    'dartino': dartino_converter,
    'dart_taskkill': dart_taskkill_converter,
    'trigger': trigger_converter,
    'win_dart_taskkill': win_dart_taskkill_converter,
    'win_dartino': win_dartino_converter,
}

def signature_match(step, signature):
  # Simple attributes are those for which an equality comparison suffices to
  # test for equality.
  simple_attributes = {'description',
                       'descriptionDone',
                       'name',
                       'workdir',
                       'mode',
                       'repourl',
                       'branch',
                       'blocksize',
                       'masterdest',
                       'slavesrc',
                       'strip'}
  subset_dictionary_attributes = {'env'}
  special_attributes = {'command'}
  all_attributes = simple_attributes | special_attributes | \
      subset_dictionary_attributes

  # Specific matching functions for complex attributes
  def list_startswith(base_list, prefix_list):
    if len(prefix_list) > len(base_list):
      return False
    if cmp(base_list[:len(prefix_list)], prefix_list) != 0:
      return False
    return True

  def command_matcher(base_command, command_signature):
    if isinstance(base_command, str):
      return base_command == command_signature
    if isinstance(base_command, list):
      return list_startswith(base_command, command_signature)
    if isinstance(base_command, master.optional_arguments.ListProperties):
      return list_startswith(base_command.items, command_signature)
    return False

  def is_subdictionary(containing_dict, subdict):
    return set(subdict.items()).issubset(set(containing_dict.items()))

  attribute_match = {}
  # For simple attributes, an equality comparison suffices.
  for attribute in simple_attributes:
    attribute_match[attribute] = lambda x, y: x == y
  for attribute in subset_dictionary_attributes:
    attribute_match[attribute] = is_subdictionary
  attribute_match['command'] = command_matcher

  if step[0] != signature[0]:
    return False

  # To let the programmer (aneeshm) know which attributes need to be covered.
  for attribute in step[1]:
    if attribute not in all_attributes:
      # TODO: Should this be an error?
      sys.stderr.write("Attribute '%s' unknown to signature_match" % attribute)

  # If the step is missing an attribute from the signature, it cannot match the
  # signature.
  for attribute in signature[1]:
    if attribute not in step[1]:
      return False

  # For all attributes in the signature, match against the corresponding
  # attribute in the step.
  for attribute in signature[1]:
    if not attribute_match[attribute](step[1][attribute],
                                   signature[1][attribute]):
      return False

  # No attribute checks failed; by definition, this means that the step matched
  # the signature.
  return True


def step_matches(step):
  matches = set()
  for signature in _step_signatures:
    if signature_match(step, _step_signatures[signature]):
      matches.add(signature)
  return matches


def steplist_match_stats(steplist):
  uniquely_matched = 0
  unmatched = 0
  multiply_matched = 0
  for step in steplist:
    matches = step_matches(step)
    if len(matches) == 0:
      unmatched += 1
    elif len(matches) == 1:
      uniquely_matched += 1
    elif len(matches) > 1:
      multiply_matched += 1
    else:
      assert False, "This is impossible"
  return (uniquely_matched, unmatched, multiply_matched)


def steplist_steps_stats(steplist):
  steps_stats = collections.defaultdict(lambda: 0)
  for step in steplist:
    matches = step_matches(step)
    for step_type in matches:
      steps_stats[step_type] += 1
  return steps_stats


def extract_builder_steplist(c, builder_name):
  for builder in c['builders']:
    if builder['name'] == builder_name:
      return builder['factory'].steps

  raise KeyError("Builder not found.")


def builder_match_stats(c, builder_name):
  return steplist_match_stats(extract_builder_steplist(c, builder_name))


def builder_steps_stats(c, builder_name):
  return steplist_steps_stats(extract_builder_steplist(c, builder_name))


# Should this be split into something that operates on a list of builders, and
# another that extracts that list of builders from a config? Probably.
# TODO: see if this is needed later.
def builderlist_steps_stats(c, builder_name_list):
  builderlist_stats = collections.defaultdict(lambda: 0)
  for builder_name in builder_name_list:
    builder_stats = builder_steps_stats(c, builder_name)
    for step_type in builder_stats:
      builderlist_stats[step_type] += builder_stats[step_type]
  return builderlist_stats


def config_steps_stats(c):
  pass


def repr_report(report, baseindent='', indent='  ', base=True):
  if isinstance(report, str):
    return baseindent + report
  elif isinstance(report, list):
    ret = cStringIO.StringIO()
    for subreport in report[:-1]:
      print >> ret, repr_report(subreport, baseindent+('' if base else indent),
                                indent, False)
    ret.write(repr_report(report[-1], baseindent + ('' if base else indent),
                          indent, False))
    retstr = ret.getvalue()
    ret.close()
    return retstr

def report_step(step):
  matchset = step_matches(step)
  if len(matchset) == 0:
    return "Unmatched step: %s" % step[0].__name__
    # Dump step body here in debug mode.
  elif len(matchset) == 1:
    return matchset.pop()
    # Dump step body here in debug mode.
  elif len(matchset) > 1:
    return "Multiply matched step: %s: %s" % (step[0].__name__, repr(matchset))
    # Dump step body here in debug mode.
  else:
    assert False, "This is impossible"


def report_steplist(steplist):
  return map(report_step, steplist)


def report_builder(c, builder_name):
  report = ['Builder: %s' % builder_name]
  report.append(report_steplist(extract_builder_steplist(c, builder_name)))
  return repr_report(report)


def name_this_function(c, ActiveMaster, filename=None):
  if ActiveMaster.project_name not in _master_builder_map:
    pass # TODO
  with open(filename, 'w') if filename else sys.stdout as f:
    for builder in _master_builder_map[ActiveMaster.project_name]:
      f.write(report_builder(c, builder))
      print >> f, 'Match statistics: %s' % repr(builder_match_stats(c, builder))
      print >> f, 'Step statistics: %s' % repr(builder_steps_stats(c, builder))
      print >> f, '\n'



class recipe_skeleton(object):
  def __init__(self, master_name):
    self.master_name = master_name
    self.deps = set()
    # Required to key by buildername.
    self.deps.add('recipe_engine/properties')
    # Required for api.step.StepFailure
    self.deps.add('recipe_engine/step')
    self.builder_names_to_steps = {}
    self.tests = set()

  def generate(self, c, builder_name_list):
    for builder_name in builder_name_list:
      # build_properties is a variable that lives throughout the life of a
      # given builder's function. It is presumed to exist by bot_update, and
      # made use of wherever build properties are needed, such as to annotated
      # scripts which take or require a '--build_properties={...}' argument.
      rc = recipe_chunk()
      rc.deps.add('recipe_engine/properties')
      rc.steps.append('build_properties = api.properties.legacy()')
      builder_rc = rc + builder_to_recipe_chunk(c, builder_name)
      self.deps = self.deps | builder_rc.deps
      self.tests = self.tests | builder_rc.tests
      self.builder_names_to_steps[builder_name] = builder_rc.steps

  def report_recipe(self):
    def sanitize_builder_name(builder_name):
      return builder_name.replace(' ', '_').replace('(', '_').replace(')', '_')\
                         .replace('.', '_').replace('-', '_')
    sbn = sanitize_builder_name

    report = [
      '# Copyright %d The Chromium Authors.' % datetime.datetime.now().year +\
          ' All rights reserved.',
      '# Use of this source code is governed by a BSD-style license that can' +\
          ' be',
      '# found in the LICENSE file.',
      ''
      ]

    report.append('DEPS = [')
    report.append(map(lambda x: '\'' + x + '\',', sorted(self.deps)))
    report.append(']\n')

    # Per-builder functions.
    for builder_name in self.builder_names_to_steps:
      report.append('def %s_steps(api):' % sbn(builder_name))
      report.append(self.builder_names_to_steps[builder_name])
      report.append('\n')

    # Dispatch directory.
    report.append('dispatch_directory = {')
    dispatch_directory = []
    for builder_name in self.builder_names_to_steps:
      dispatch_directory.append("'%s': %s_steps," %(builder_name,
                                                    sbn(builder_name)))
    report.append(dispatch_directory)
    report.append('}')
    report.append('\n')

    # Builder dispatch.
    report.append('def RunSteps(api):')
    steps = ['if api.properties["buildername"] not in dispatch_directory:',
              ['raise api.step.StepFailure("Builder unsupported by recipe.")'],
              'else:',
              ['dispatch_directory[api.properties["buildername"]](api)'],
            ]
    report.append(steps)
    report.append('')

    # Generate tests.
    report.append('def GenTests(api):')
    for builder_name in self.builder_names_to_steps:
      test_properties = ["api.properties(mastername='%s') +" % self.master_name,
                         "api.properties(buildername='%s') +" % builder_name,
                         "api.properties(revision='123456789abcdef') +",
                         "api.properties(slavename='%s')" % "TestSlave",]
      test = ["yield (api.test('%s') +" % sbn(builder_name)] +\
             [test_properties] +\
             ['      )']
      report.append(test)
    test = [
        "yield (api.test('builder_not_in_dispatch_directory') +",
        [
         "api.properties(mastername='%s') +" % self.master_name,
         "api.properties(buildername='nonexistent_builder') +",
         "api.properties(slavename='TestSlave')"
        ],
        "      )",
        ]
    report.append(test)

    return repr_report(report)

def builder_to_recipe_chunk(c, builder_name):
  return steplist_to_recipe_chunk(extract_builder_steplist(c, builder_name))


def steplist_to_recipe_chunk(steplist):
  return sum(map(step_to_recipe_chunk, steplist), recipe_chunk())


# Fails if a step cannot be converted. Perhaps add graceful degradation later,
# iff required. Pass for now, while testing.
def step_to_recipe_chunk(step):
  logging.debug("step_to_recipe_chunk called")
  logging.debug("Raw step")
  logging.debug(pprint.pformat(step))
  matches = step_matches(step)
  logging.debug("Matches:")
  logging.debug(pprint.pformat(matches))
  if len(matches) != 1:
    logging.debug("Unconvertible step; calling dump_converter")
    ret = dump_converter(step, 'step matched %d times' % len(matches))
    logging.debug("dump_converted step:")
    logging.debug(ret)
    return ret
  step_type = matches.pop()
  if step_type not in _step_converters_map:
    return dump_converter(step, 'step recognised, no converter found')
  return _step_converters_map[step_type](step)

def write_recipe(c, ActiveMaster, filename=None):
  global _GLOBAL_BUILDMASTER_CONFIG
  _GLOBAL_BUILDMASTER_CONFIG = c
  if ActiveMaster.project_name not in _master_builder_map:
    pass # TODO
  rs = recipe_skeleton(_master_name_map[ActiveMaster.project_name])
  rs.generate(c, _master_builder_map[ActiveMaster.project_name])
  filename = filename or _master_name_map[ActiveMaster.project_name] +\
      '.recipe_autogen.py'
  with open(filename, 'w') as f:
    f.write(rs.report_recipe())

def write_builderlist_converted(c, buildername, filename):
  builder_steplist = extract_builder_steplist(c, buildername)
  with open(filename, 'w') as f:
    print >> f, "%d" % len(builder_steplist)
    i = 0
    for step in builder_steplist:
      print >> f, ">>> Step %d raw:" % i
      print >> f, pprint.pformat(step, indent=2)
      print >> f, ">>> Step %d converted:" % i
      print >> f, step_to_recipe_chunk(step)
      i = i + 1

def write_step(c, buildername, stepnumber, filename):
  step = extract_builder_steplist(c, buildername)[stepnumber]
  with open(filename, 'w') as f:
    print >> f, ">>> Raw"
    print >> f, pprint.pformat(step)
    print >> f, ">>> Converted"
    print >> f, step_to_recipe_chunk(step)

def write_numsteps_builder(c, buildername, filename):
  with open(filename, 'w') as f:
    f.write(str(len(extract_builder_steplist(c, buildername))))

def write_builder_steplist(c, builder_name, filename):
  with open(filename, 'w') as f:
    f.write(pprint.pformat(extract_builder_steplist(c, builder_name), indent=2))
