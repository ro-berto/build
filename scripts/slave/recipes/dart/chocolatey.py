# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

DEPS = [
  'depot_tools/cipd',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'recipe_engine/url',
]

INSTALLER_NAME = 'install.ps1'
INSTALLER = 'https://chocolatey.org/%s' % INSTALLER_NAME
POWERSHELL = (
  'C:\\\\WINDOWS\\\\system32\\\\WindowsPowerShell\\\\v1.0\\\\powershell.exe')
CHECKSUM = ('https://storage.googleapis.com/dart-archive/'
  'channels/%s/release/%s/sdk/dartsdk-windows-%s-release.zip.sha256sum')

def RunSteps(api):
  package = api.properties.get('package', 'dart-sdk')
  version = api.properties.get('version')
  channel = 'dev' if '-dev' in version else 'stable'

  installer_path = api.path['cleanup'].join(INSTALLER_NAME)
  api.url.get_file(INSTALLER, installer_path, 'download chocolatey installer')

  choco_home = api.path['cleanup'].join('chocolatey')
  bin_root = api.path['cleanup'].join('bin_root')
  env = {
    'ChocolateyInstall': choco_home,
    'ChocolateyBinRoot': bin_root
  }
  with api.context(env=env):
    api.step('install chocolatey', [POWERSHELL, installer_path])

    choco = choco_home.join('choco')
    api.step('choco --version', [choco, '--version'])

    cache = api.path['cleanup'].join('cache')
    api.step('choco set package directory',
             [choco, 'config', 'set', 'cacheLocation', cache])

    cloudkms_dir = api.path['start_dir'].join('cloudkms')
    api.cipd.ensure(cloudkms_dir,
                    {'infra/tools/luci/cloudkms/${platform}': 'latest'})

    api.gsutil.download('dart-ci-credentials',
                        'chocolatey.encrypted',
                        'chocolatey.encrypted')

    chocolatey_key = api.path['cleanup'].join('chocolatey.key')
    api.step('cloudkms get API key', [
             cloudkms_dir.join('cloudkms.exe'), 'decrypt',
             '-input', 'chocolatey.encrypted',
             '-output', chocolatey_key, 'dart-ci/us-central1/dart-ci/dart-ci'])

    # todo(athom): Use git recipe module instead if bug 785362 is ever fixed.
    api.step(
      'checkout chocolatey-packages',
      ['git', 'clone', 'https://github.com/dart-lang/chocolatey-packages.git'])

    checksum = api.url.get_text(CHECKSUM % (channel, version, 'ia32'),
                                default_test_data='abc *should-not-see-this')
    checksum = checksum.output.split()[0]
    checksum64 = api.url.get_text(CHECKSUM % (channel, version, 'x64'),
                                  default_test_data='def *should-not-see-this')
    checksum64 = checksum64.output.split()[0]

    chocolatey_dir = api.path['start_dir'].join('chocolatey-packages')
    package_dir = chocolatey_dir.join(package)
    installer_path = package_dir.join('chocolateyInstall.ps1')
    installer = api.file.read_text('read installer', installer_path)

    installer = installer.replace('$version$', version)
    installer = installer.replace('$channel$', channel)
    installer = installer.replace('$checksum$', checksum)
    installer = installer.replace('$checksum64$', checksum64)

    api.file.write_text('write installer', installer_path, installer)

    with api.context(cwd=package_dir):
      if channel == 'dev':
        # todo(athom): remove when chocolatey supports semver 2.0.0 properly
        # 2.0.0-dev.22.0 -> 2.0.0.22-dev
        (version, build) = version.split('-')
        (channel, build_number, fix) = build.split('.')
        version = "%s.%s-dev-%s" % (version, build_number, fix)

      api.step('choco pack', [choco, 'pack', 'version=%s' % version])

      api.step('verify with choco install', [
        choco, 'install', package, '--pre', '-y', '-dv', '-s', '.'])

      choco_push = '$secret = cat %s; %s push -k="$secret" %s.%s.nupkg' % (
        chocolatey_key, choco, package, version)
      api.step('choco push', [POWERSHELL, '-Command', choco_push])

def GenTests(api):
  yield (
    api.test('dev') +
    api.properties.generic(version='2.0.0-dev.51.0') +
    api.post_process(Filter('choco pack', 'choco push'))
  )
  yield (
    api.test('release') +
    api.properties.generic(
      version='1.24.3')
  )
