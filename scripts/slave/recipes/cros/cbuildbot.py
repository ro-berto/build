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

  # Run a debug build if instructed.
  if api.properties.get('cbb_debug'):
    api.chromite.c.cbb.debug = True

  # TODO(dnj): Deprecate master-driven build ID passing.
  master_build_id = api.properties.get('master_build_id')
  if master_build_id:
    api.chromite.c.cbb.build_id = master_build_id

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
          revision=api.gitiles.make_hash('test'),
      )
  )

  # Test a CrOS build with missing revision/repository properties.
  yield (
      api.test('cros_manifest')
      + api.properties(
          cbb_config='x86-generic-full',
          mastername='chromiumos.chromium',
          buildername='Test',
          slavename='test',
          buildnumber='12345',
          branch='testbranch',
          repository='https://chromium.googlesource.com/chromiumos/'
                     'manifest-versions',
          revision=api.gitiles.make_hash('test'),
      )
      + api.step_data(
          'Fetch build ID',
          api.gitiles.make_commit_test_data(
              'test',
              '\n'.join([
                  'Commit message!',
                  'CrOS-Build-Id: 1337',
              ]),
          ),
      )
  )

  # Test a legacy (pre-recipe) CrOS build
  # TODO(dnj): remove this once updated
  yield (
      api.test('legacy_build_id')
      + api.properties(
          cbb_config='x86-generic-full',
          mastername='chromiumos',
          buildername='Test',
          slavename='test',
          buildnumber='12345',
          master_build_id='1337',
          repository='https://chromium.googlesource.com/chromiumos/src',
          revision=api.gitiles.make_hash('test'),
      )
  )
