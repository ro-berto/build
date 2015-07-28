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

def _CheckoutSteps(api):
  api.gclient.set_config('nacl')
  # TODO: check if the 'DEPS' in the solution in my home directory means
  # anything.
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()

def _AnnotatedStepsSteps(api):
  api.python('annotated steps',
      api.path['checkout'].join('buildbot', 'buildbot_selector.py'),
      allow_subannotations=True,
      cwd = api.path['checkout'],
      env = {'BUILDBOT_MASTERNAME': api.properties['mastername'],
        'BUILDBOT_BUILDERNAME': api.properties['buildername'],
        'BUILDBOT_REVISION': api.properties['revision'],
        'RUNTEST': api.path['build'].join('scripts', 'slave', 'runtest.py'),
        # NOTE: If this recipe is used for a tryserver/trybots, please change
        # 'BuilderTester' to 'Trybot'.
        'BUILDBOT_SLAVE_TYPE': 'BuilderTester',
        })

def _TriggerTestsSteps(api):
  trigger_map = {
      'precise_64-newlib-arm_qemu-pnacl-dbg':
        'oneiric_32-newlib-arm_hw-pnacl-panda-dbg',
      'precise_64-newlib-arm_qemu-pnacl-opt':
        'oneiric_32-newlib-arm_hw-pnacl-panda-opt',
      'precise_64-newlib-arm_qemu-pnacl-buildonly-spec':
        'oneiric_32-newlib-arm_hw-pnacl-panda-spec',
      }

  if api.properties['buildername'] in trigger_map:
    api.trigger(
        {'builder_name': trigger_map[api.properties['buildername']]})

def RunSteps(api):
  _CheckoutSteps(api)
  _AnnotatedStepsSteps(api)
  _TriggerTestsSteps(api)

def GenTests(api):
  # yield api.test('win') + api.platform('win', 64)
  yield api.test('linux') + api.platform('linux', 64) + \
    api.properties(mastername = 'client.nacl') + \
    api.properties(buildername = 'precise_64-newlib-arm_qemu-pnacl-dbg') +\
    api.properties(revision = 'abcd') +\
    api.properties(slavename='TestSlave')
