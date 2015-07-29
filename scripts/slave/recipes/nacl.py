# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
  'trigger',
]

# TODO list:
# Consolidate the build process as much as possible. (optional, but strongly
#   desired.)
# e-mail thread from Pawel about the Mac bots not using compile.py, causing
#   goma errors.
# Remove this todo list.

# Maps from triggering builder to triggered builder;
# key builder triggers value builder.
trigger_map = {
    'precise_64-newlib-arm_qemu-pnacl-dbg':
      'oneiric_32-newlib-arm_hw-pnacl-panda-dbg',
    'precise_64-newlib-arm_qemu-pnacl-opt':
      'oneiric_32-newlib-arm_hw-pnacl-panda-opt',
    'precise_64-newlib-arm_qemu-pnacl-buildonly-spec':
      'oneiric_32-newlib-arm_hw-pnacl-panda-spec',
}

def _CheckoutSteps(api):
  api.gclient.set_config('nacl')
  # TODO: check if the 'DEPS' in the solution in my home directory means
  # anything.
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()

def _AnnotatedStepsSteps(api):
  # Default environemnt; required by all builders.
  env = {
      'BUILDBOT_MASTERNAME': api.properties['mastername'],
      'BUILDBOT_BUILDERNAME': api.properties['buildername'],
      'BUILDBOT_REVISION': api.properties['revision'],
      'RUNTEST': api.path['build'].join('scripts', 'slave', 'runtest.py'),
      # NOTE: If this recipe is used for a tryserver/trybots, please change
      # 'BuilderTester' to 'Trybot'.
      'BUILDBOT_SLAVE_TYPE': 'BuilderTester',
  }
  # Set up env for the triggered builders.
  if api.properties['buildername'] in trigger_map.values():
    env.update({
        'BUILDBOT_TRIGGERED_BY_BUILDERNAME':
          api.properties['triggered_by_buildername'],
        'BUILDBOT_TRIGGERED_BY_BUILDNUMBER':
          api.properties['triggered_by_buildnumber'],
        'BUILDBOT_TRIGGERED_BY_REVISION':
          api.properties['triggered_by_revision'],
        'BUILDBOT_TRIGGERED_BY_SLAVENAME':
          api.properties['triggered_by_slavename'],
    })
  api.python('annotated steps',
      api.path['checkout'].join('buildbot', 'buildbot_selector.py'),
      allow_subannotations=True,
      cwd = api.path['checkout'],
      env = env,
    )

def _TriggerTestsSteps(api):

  if api.properties['buildername'] in trigger_map:
    api.trigger(
        {'builder_name': trigger_map[api.properties['buildername']]})

def RunSteps(api):
  _CheckoutSteps(api)
  _AnnotatedStepsSteps(api)
  _TriggerTestsSteps(api)

def GenTests(api):
  yield api.test('linux_triggering') +\
    api.platform('linux', 64) +\
    api.properties(mastername = 'client.nacl') +\
    api.properties(buildername = 'precise_64-newlib-arm_qemu-pnacl-dbg') +\
    api.properties(revision = 'abcd') +\
    api.properties(slavename='TestSlave')
  yield api.test('linux_triggered') +\
    api.platform('linux', 32) +\
    api.properties(mastername = 'client.nacl') +\
    api.properties(buildername = 'oneiric_32-newlib-arm_hw-pnacl-panda-dbg') +\
    api.properties(revision = 'abcd') +\
    api.properties(slavename='TestSlave') +\
    api.properties(triggered_by_revision = 'abcd') +\
    api.properties(triggered_by_slavename = 'TestSlave') +\
    api.properties(triggered_by_buildername =
        'precise_64-newlib-arm_qemu-pnacl-dbg') +\
    api.properties(triggered_by_buildnumber = '1')
