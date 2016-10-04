# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import re


DEPS = [
  'depot_tools/cipd',
  'gae_sdk',
  'gsutil',
  'recipe_engine/path',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'zip',
]

# CIPD builder service account, deployed by Puppet.
_CIPD_CREDENTIAL_PATH = ('/creds/service_accounts/'
                         'service-account-cipd-builder.json')


def RunSteps(api):
  pb = _PackageBuilder(api)

  # Determine the current GAE SDK version.
  try:
    version = pb.latest_upstream_version()
  except pb.VersionParseError as e:
    api.python.failing_step('Version Fetch',
        'Failed to fetch latest version: %s' % (e,))

  # Make sure the CIPD client is installed.
  api.cipd.install_client()
  api.cipd.set_service_account_credentials(_CIPD_CREDENTIAL_PATH)

  # Iterate over all of the GAE SDK packages and build any that don't exist.
  version_tag = pb.version_tag(version)
  pkg_outdir = api.path.mkdtemp('gae_sdk_package')
  for plat, arch in api.gae_sdk.all_packages:
    pkg_name = api.gae_sdk.package(plat, arch=arch)
    with api.step.nest('Sync %s' % (pkg_name,)):
      step = api.cipd.search(pkg_name, '%s:%s' % (version_tag))
      if len(step.json.output['result']) > 0:
        api.python.succeeding_step('Synced', 'Package is up to date.')
        continue

      # Create a temporary directory to build the package in.
      pkg_base = pb.download_and_unpack(plat, arch, version)

      # Build and register our CIPD package.
      pkg_path = pkg_outdir.join('gae_sdk_%s_%s.pkg' % (plat, arch))
      api.cipd.build(
          pkg_base,
          pkg_path,
          pkg_name,
          install_mode='copy',
      )
      api.cipd.register(
          pkg_name,
          pkg_path,
          refs=[api.gae_sdk.latest_ref],
          tags={version_tag[0]: version_tag[1]},
      )


class _PackageBuilder(object):
  # The Google Storage GAE SDK bucket base. All SDK packages are stored in here
  # under a basename + version ZIP file.
  _GS_BUCKET_BASE = 'gs://appengine-sdks/featured'
  # The GS path to the "LATEST" YAML file.
  _GS_VERSION_YAML = '%s/VERSION' % (_GS_BUCKET_BASE,)

  # Hacky regex for the "release" YAML variable.
  _RE_RELEASE = re.compile(r'^release:\s+"([^"]+)"$')

  class VersionParseError(Exception):
    pass

  def __init__(self, api):
    self._api = api

  def version_tag(self, version):
    return ('gae_sdk_version', version)

  @property
  def api(self):
    return self._api

  def latest_upstream_version(self):
    step_result = self.api.gsutil.cat(
        self._GS_VERSION_YAML,
        name='Get Latest',
        stdout=self.api.raw_io.output())
    latest = self._parse_latest_yaml(step_result.stdout)
    step_result.presentation.step_text += ' %s' % (latest,)
    return latest

  @classmethod
  def _parse_latest_yaml(cls, text):
    # Rather than import a YAML parser, we will specifically search for the
    # string:
    #
    # release: "<version>"
    for line in text.splitlines():
      m = cls._RE_RELEASE.match(line)
      if m:
        return m.group(1)
    raise cls.VersionParseError('Could not parse release version from YAML.')

  def download_and_unpack(self, plat, arch, version):
    # Get the package base for this OS.
    _, base, dirname = self.api.gae_sdk.package_spec(plat, arch)
    name = '%s%s.zip' % (base, version)
    artifact_url = '%s/%s' % (self._GS_BUCKET_BASE, name)

    tdir = self.api.path.mkdtemp('gae_sdk')
    dst = tdir.join(name) # Store the ZIP file here.
    unzip_dir = tdir.join('unpack') # Unzip contents here.
    self.api.gsutil.download_url(
        artifact_url,
        dst,
        name='Download %s %s' % (plat, arch,))
    self.api.zip.unzip(
        'Unzip %s %s' % (plat, arch),
        dst,
        unzip_dir,
        quiet=True)

    pkg_dir = unzip_dir.join(dirname)
    self.api.path.mock_add_paths(pkg_dir)
    assert self.api.path.exists(pkg_dir), (
        'Package directory [%s] does not exist' % (pkg_dir,))
    return pkg_dir


def GenTests(api):
  LATEST_YAML = '\n'.join((
    'release: "1.2.3"',
    'foo: bar',
    'baz:',
    '  - qux',
  ))

  def cipd_pkg(plat, pkg_base, exists):
    pkg_name = 'infra/gae_sdk/%s/%s' % (plat, pkg_base)
    cipd_step = 'cipd search %s gae_sdk_version:1.2.3' % (pkg_name,)
    instances = (2) if exists else (0)
    return api.step_data('Sync %s.%s' % (pkg_name, cipd_step),
          api.cipd.example_search(pkg_name, instances=instances))

  yield (api.test('packages') +
      api.step_data('gsutil Get Latest',
          api.raw_io.stream_output(LATEST_YAML, stream='stdout')) +
      cipd_pkg('go', 'linux-amd64', False) +
      cipd_pkg('go', 'linux-386', True) +
      cipd_pkg('go', 'mac-amd64', True) +
      cipd_pkg('python', 'all', False))

  yield (api.test('bad_version_yaml') +
      api.step_data('gsutil Get Latest',
          api.raw_io.stream_output('', stream='stdout')))
