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
]

# TODO list:
# Convert this to use bot_update.
# Convert this to use GOMA.
# Consolidate the build process as much as possible. (optional, but strongly
#   desired.)
# e-mail thread from Pawel about the Mac bots not using compile.py, causing
#   goma errors.
# Check if gclient runhooks should run before or after the cleanuptemp and
# clobber steps.
# Check whether allow_subannotations=True propagates environment variables;
#   fix it if it doesn't.
# Remove the test env data.
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
        'RUNTEST': api.path['build'].join('scripts', 'slave', 'runtest.py')})
#      env = {'BUILDBOT_MASTERNAME': 'client.nacl',
#        'BUILDBOT_BUILDERNAME': 'precise-64-newlib-opt-test',
#        'BUILDBOT_REVISION': ,
#        # Required by the buildbot_selector.
#        'RUNTEST': api.path['build'].join('scripts', 'slave', 'runtest.py')})

def RunSteps(api):
  _CheckoutSteps(api)
  _AnnotatedStepsSteps(api)

def GenTests(api):
  # yield api.test('win') + api.platform('win', 64)
  yield api.test('linux') + api.platform('linux', 64) + \
    api.properties(mastername = 'client.nacl') + \
    api.properties(buildername = 'precise-64-newlib-opt-test') +\
    api.properties(revision = 'abcd') +\
    api.properties(slavename='TestSlave')
