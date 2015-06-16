# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from common import cros_chromite

DEPS = [
  'chromite',
  'gitiles',
  'properties',
]

# Map master name to 'chromite' configuration name.
_MASTER_CONFIG_MAP = {
    'chromiumos.tryserver': {
      'master_config': 'external',
      'variants': {
        'etc': ['chromeos_tryserver_etc'],
      },
    },
}


# Testing: Tryjob data file JSON.
_TRYJOB_DATA = """
{
  "name": "12345",
  "email": "testauthor@fake.chromium.org",
  "extra_args": [
    "--timeout",
    "14400",
    "--remote-trybot",
    "--remote-version=4"
  ]
}
"""


def RunSteps(api):
  # The 'cbuildbot' config name to build is the name of the builder.
  cbb_config_name = api.properties.get('buildername')
  cbb = cros_chromite.Get()
  cbb_config = cbb.get(cbb_config_name)

  # Apply our generic configuration.
  api.chromite.configure(
      api.properties,
      _MASTER_CONFIG_MAP)

  # Determine our build directory name.
  namebase = cbb_config_name
  if cbb_config:
    namebase = 'internal' if cbb_config.get('internal') else 'external'
  api.chromite.c.cbb.builddir = '%s_master' % (namebase,)

  # Run our 'cbuildbot'.
  api.chromite.run_cbuildbot(
      cbb_config_name,
      tryjob=True)


def GenTests(api):
  # Test a CrOS tryjob.
  yield (
      api.test('basic')
      + api.properties(
          mastername='chromiumos.tryserver',
          buildername='x86-generic-full',
          slavename='test',
          repository='https://chromium.googlesource.com/chromiumos/tryjobs.git',
          revision=api.gitiles.make_hash('test'),
      )
      + api.step_data(
          'Fetch tryjob commit',
          api.gitiles.make_commit_test_data(
              'test',
              '\n'.join([
                  'Commit message!',
              ]),
              new_files=['user/user.12345'],
          ),
      )
      + api.step_data(
          'Fetch tryjob descriptor (user/user.12345)',
          api.gitiles.make_encoded_file(_TRYJOB_DATA)
      )
  )

  # Test an 'etc' job (no Chromite config).
  yield (
      api.test('etc')
      + api.properties(
          mastername='chromiumos.tryserver',
          buildername='etc',
          slavename='test',
          cbb_variant='etc',
          repository='https://chromium.googlesource.com/chromiumos/tryjobs.git',
          revision=api.gitiles.make_hash('test'),
      )
      + api.step_data(
          'Fetch tryjob commit',
          api.gitiles.make_commit_test_data(
              'test',
              '\n'.join([
                  'Commit message!',
              ]),
              new_files=['user/user.12345'],
          ),
      )
      + api.step_data(
          'Fetch tryjob descriptor (user/user.12345)',
          api.gitiles.make_encoded_file(_TRYJOB_DATA)
      )
  )

  # Test an invalid CrOS tryjob (no files in commit).
  yield (
      api.test('basic_no_files_in_commit')
      + api.properties(
          mastername='chromiumos.tryserver',
          buildername='x86-generic-full',
          slavename='test',
          repository='https://chromium.googlesource.com/chromiumos/tryjobs.git',
          revision=api.gitiles.make_hash('test'),
      )
      + api.step_data(
          'Fetch tryjob commit',
          api.gitiles.make_commit_test_data(
              'test',
              '\n'.join([
                  'Commit message!',
              ]),
          ),
      )
  )
