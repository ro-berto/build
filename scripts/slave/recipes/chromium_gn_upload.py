# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/cipd',
  'depot_tools/depot_tools',
  'depot_tools/gsutil',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]


BUILDERS = {
  'tryserver.chromium.linux': {
    'builders': {
      'linux_chromium_gn_upload': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['clobber'],

        # We need this to pull the Linux sysroots.
        'gclient_apply_config': ['chrome_internal'],
      },
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
      'mac_chromium_gn_upload': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['clobber'],
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win_chromium_gn_upload': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
        'chromium_apply_config': ['clobber'],
      },
    },
  },
}


def b(master, builder):
  return BUILDERS[master]['builders'][builder]


# Equivalent LUCI-based builders (all in a single bucket).
BUILDERS['luci.infra-internal.triggered'] = {
  'builders': {
    'gn-builder-linux':
        b('tryserver.chromium.linux', 'linux_chromium_gn_upload'),
    'gn-builder-mac': b('tryserver.chromium.mac', 'mac_chromium_gn_upload'),
    'gn-builder-win': b('tryserver.chromium.win', 'win_chromium_gn_upload'),
  },
}

BUILDERS = freeze(BUILDERS)


CIPD_PKGS = freeze({
  'gn-builder-linux': 'infra/tools/gn/linux-amd64',
  'gn-builder-mac': 'infra/tools/gn/mac-amd64',
  'gn-builder-win': 'infra/tools/gn/windows-386',
})


def upload_to_cipd(api, buildername, rel_dir, gn_exe, gn_version, git_revision):
  # Switch to using default task account on LUCI for cipd auth.
  api.cipd.set_service_account_credentials(None)

  cipd_pkg_name = CIPD_PKGS[buildername]
  step = api.cipd.search(cipd_pkg_name, 'gn_version:%s' % gn_version)
  if step.json.output['result']:
    api.step('Package is up-to-date', cmd=None)
    return

  pkg_def = api.cipd.PackageDefinition(
      package_name=cipd_pkg_name,
      package_root=rel_dir,
      install_mode='copy')
  pkg_def.add_file(rel_dir.join(gn_exe))
  pkg_def.add_version_file('.versions/%s.cipd_version' % gn_exe)

  api.cipd.create_from_pkg(
      pkg_def,
      refs=['latest'],
      tags={
        'gn_version': gn_version,
        'git_repository': 'https://chromium.googlesource.com/chromium/src',
        'git_revision': git_revision,
      }
  )


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS,
                                                       ['gn_for_uploads', 'mb'])

  bot_update_step = api.bot_update.ensure_checkout(
      patch_root=bot_config.get('root_override'))
  git_revision = bot_update_step.presentation.properties['got_revision']

  api.chromium.ensure_goma()

  api.chromium.runhooks()

  api.chromium.run_mb(mastername, buildername)

  api.chromium.compile(targets=['gn', 'gn_unittests'], use_goma_module=True)

  gn_exe = 'gn' if not api.platform.is_win else 'gn.exe'
  rel_dir = api.path['checkout'].join('out', 'Release')
  path_to_binary = rel_dir.join(gn_exe)
  path_to_sha1 = rel_dir.join(gn_exe + '.sha1')

  step = api.step('gn version', [path_to_binary, '--version'],
                  stdout=api.raw_io.output())
  gn_version = step.stdout.strip()

  api.chromium.runtest('gn_unittests')

  if not api.platform.is_win:
    api.m.step('gn strip', cmd=['strip', path_to_binary])

  api.python(
      'upload',
      api.depot_tools.upload_to_google_storage_path,
      ['-b', 'chromium-gn', path_to_binary])

  sha1 = api.file.read_text(
      'gn sha1', path_to_sha1,
      test_data='0123456789abcdeffedcba987654321012345678')
  api.step.active_result.presentation.step_text = sha1

  if mastername == 'luci.infra-internal.triggered':
    upload_to_cipd(api, buildername, rel_dir, gn_exe, gn_version, git_revision)


def GenTests(api):
  GN_VERSION = '12345'
  def version():
    return api.step_data('gn version', api.raw_io.stream_output(GN_VERSION))

  def cipd_pkg(buildername, exists):
    pkg_name = CIPD_PKGS[buildername]
    cipd_step = 'cipd search %s gn_version:%s' % (pkg_name, GN_VERSION)
    instances = (2) if exists else (0)
    return api.step_data(cipd_step,
        api.cipd.example_search(pkg_name, instances=instances))

  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    if test.properties['mastername'] == 'luci.infra-internal.triggered':
      exists = 'mac' in test.properties['buildername']
      yield test + version() + cipd_pkg(test.properties['buildername'], exists)
    else:
      yield test
