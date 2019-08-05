# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromite',
  'depot_tools/gitiles',
  'recipe_engine/buildbucket',
  'recipe_engine/properties',
]


# Map master name to 'chromite' configuration name.
_MASTER_CONFIG_MAP = {
  'chromiumos': {
    'master_config': 'master_chromiumos',
  },
  'chromiumos.chromium': {
    'master_config': 'master_chromiumos_chromium',
    # per-builder settings
    'builder_config': {
      'amd64-generic-goma-canary-chromium-pfq-informational': 'use_goma_canary',
    },
  },

  # Fake master name for Coverage.
  'chromiumos.coverage': {
    'master_config': 'chromiumos_coverage',
  },
}

def RunSteps(api):
  # Load the appropriate configuration based on the master.
  api.chromite.configure(
      api.properties,
      _MASTER_CONFIG_MAP)

  # Run 'cbuildbot' common recipe.
  api.chromite.run_cbuildbot(args=['--buildbot'],
                             goma_canary=api.chromite.c.use_goma_canary)


def GenTests(api):
  import json

  common_properties = {
      'buildername': 'Test',
      # chromite module uses path['root'] which exists only in Buildbot.
      'path_config': 'buildbot',
      'bot_id': 'test',
  }

  #
  # master.chromiumos.chromium
  #

  # Test a standard CrOS build triggered by a Chromium commit.
  yield (api.test('swarming_builder') + api.properties(
      bot_id='test',
      path_config='generic',
      cbb_config='swarming-build-config',
  ))

  # Test a standard CrOS build triggered by a Chromium commit.
  yield (api.test('chromiumos_chromium_builder') + api.properties(
      mastername='chromiumos.chromium',
      cbb_config='x86-generic-tot-chrome-pfq-informational',
      **common_properties) + api.buildbucket.try_build(
          builder='chromiumos.chromium',
          build_number=12345,
          git_repo='https://chromium.googlesource.com/chromium/src',
          revision='b8819267417da248aa4fe829c5fcf0965e17b0c3'))

  #
  # master.chromiumos
  #

  # Test a ChromiumOS Paladin build.
  yield (api.test('chromiumos_paladin') + api.properties(
      mastername='chromiumos',
      cbb_config='x86-generic-paladin',
      **common_properties) + api.buildbucket.try_build(
          builder='chromiumos',
          build_number=12345,
          git_repo='https://chromium.googlesource.com/chromiumos/'
          'manifest-versions',
          revision=api.gitiles.make_hash('test')) + api.step_data(
              'Fetch manifest config',
              api.gitiles.make_commit_test_data(
                  'test',
                  '\n'.join([
                      'Commit message!',
                      'Automatic: Start master-paladin master 6952.0.0-rc4',
                      'CrOS-Build-Id: 1337',
                  ]),
              ),
          ))

  # Test a ChromiumOS Paladin build whose manifest is not parsable.
  yield (api.test('chromiumos_paladin_manifest_failure') + api.properties(
      mastername='chromiumos',
      cbb_config='x86-generic-paladin',
      **common_properties) + api.buildbucket.try_build(
          builder='chromiumos',
          build_number=12345,
          git_repo='https://chromium.googlesource.com/chromiumos/'
          'manifest-versions',
          revision=api.gitiles.make_hash('test')) + api.step_data(
              'Fetch manifest config',
              api.gitiles.make_commit_test_data('test', None)))

  # Test a ChromiumOS Paladin build that was configured using BuildBucket
  # instead of a manifest.
  yield (api.test('chromiumos_paladin_buildbucket') + api.properties(
      mastername='chromiumos',
      buildnumber='12345',
      cbb_config='auron-paladin',
      cbb_branch='master',
      cbb_master_build_id='24601',
      repository='https://chromium.googlesource.com/chromiumos/'
      'manifest-versions',
      revision=api.gitiles.make_hash('test'),
      buildbucket=json.dumps({
          'build': {
              'id': '1337',
          },
      }),
      **common_properties))

  # Test with a property use_goma_canary=True.
  yield (api.test('chromiumos_goma_canary') + api.properties(
      mastername='chromiumos.chromium',
      buildername='amd64-generic-goma-canary-chromium-pfq-informational',
      buildnumber='12345',
      cbb_config='amd64-generic-goma-canary-chromium-pfq-informational',
      cbb_branch='master',
      cbb_master_build_id='24601',
      repository='https://chromium.googlesource.com/chromiumos/'
      'manifest-versions',
      revision=api.gitiles.make_hash('test'),
      buildbucket=json.dumps({
          'build': {
              'id': '1337',
          },
      }),
      path_config='buildbot',
      bot_id='test',
  ))

  #
  # [Coverage]
  #

  # Coverage builders for a bunch of options used in other repositories.
  yield (api.test('chromiumos_coverage') + api.properties(
      mastername='chromiumos.coverage',
      clobber=None,
      cbb_config='x86-generic-full',
      cbb_branch='firmware-uboot_v2-1299.B',
      config_repo='https://fake.googlesource.com/myconfig/repo.git',
      cbb_debug=True,
      cbb_disable_branch=True,
      **common_properties) + api.buildbucket.try_build(
          builder='chromiumos.coverage',
          build_number=1234,
          git_repo='https://chromium.googlesource.com/chromiumos/'
          'chromite.git',
          revision='fdea0dde664e229976ddb2224328da152fba15b1'))

  # Coverage builders for a bunch of options used in other repositories.
  # This one uses a variant system.
  #
  # TODO(dnj): Remove this once variant support is deleted.
  yield (api.test('chromiumos_coverage_variant') + api.properties(
      mastername='chromiumos.coverage',
      clobber=None,
      cbb_variant='coverage',
      cbb_config='x86-generic-full',
      cbb_branch='firmware-uboot_v2-1299.B',
      cbb_debug=True,
      cbb_disable_branch=True,
      config_repo='https://fake.googlesource.com/myconfig/repo.git',
      **common_properties) + api.buildbucket.try_build(
          builder='chromiumos.coverage',
          build_number=1234,
          git_repo='https://chromium.googlesource.com/chromiumos/'
          'chromite.git',
          revision='fdea0dde664e229976ddb2224328da152fba15b1'))
