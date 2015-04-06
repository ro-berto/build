# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromite',
  'gitiles',
  'properties',
]


# Map master name to 'chromite' configuration name.
_MASTER_CONFIG_MAP = {
  'chromiumos': {
    'master_config': 'master_chromiumos',
    'variants': {
      'test': ['test_variant'],
    },
  },
  'chromiumos.chromium': {
    'master_config': 'master_chromiumos_chromium',
  },
}

def GenSteps(api):
  # Load the appropriate configuration based on the master.
  api.chromite.configure(
      _MASTER_CONFIG_MAP,
      api.properties['mastername'],
      variant=api.properties.get('cbb_variant'))

  # If a Chromite branch is supplied, use it to override the default Chromite
  # checkout revision.
  if api.properties.get('cbb_branch'):
    api.chromite.c.chromite_revision = api.properties['cbb_branch']

  # Run a debug build if instructed.
  if api.properties.get('cbb_debug'):
    api.chromite.c.cbb.debug = True

  # Run 'cbuildbot' common recipe.
  api.chromite.run_cbuildbot(
        api.properties['cbb_config'])

def GenTests(api):
  # Test a standard CrOS build triggered by a Chromium commit.
  yield (
      api.test('basic_chromium_repo')
      + api.properties(
          cbb_config='x86-generic-full',
          cbb_debug=True,
          cbb_variant='test',
          mastername='chromiumos',
          buildername='Test',
          slavename='test',
          buildnumber='12345',
          repository='https://chromium.googlesource.com/chromium/src.git',
          branch='master',
          revision=api.gitiles.make_hash('test'),
      )
  )

  # Test a CrOS build with missing revision/repository properties.
  yield (
      api.test('cros_manifest')
      + api.properties(
          cbb_config='x86-generic-full',
          cbb_branch='testbranch',
          mastername='chromiumos.chromium',
          buildername='Test',
          slavename='test',
          buildnumber='12345',
          repository='https://chromium.googlesource.com/chromiumos/'
                     'manifest-versions',
          branch='master',
          revision=api.gitiles.make_hash('test'),
      )
      + api.step_data(
          'Fetch manifest config',
          api.gitiles.make_commit_test_data(
              'test',
              '\n'.join([
                  'Commit message!',
                  'Automatic: Start builder use-this-revision miscdata foo bar',
                  'CrOS-Build-Id: 1337',
              ]),
          ),
      )
  )
