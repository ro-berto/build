# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test v8/node.js integration."""

from recipe_engine.types import freeze


DEPS = [
  'chromium',
  'depot_tools/gclient',
  'file',
  'gsutil',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'v8',
  'zip',
]

BUILDERS = freeze({
  'client.v8.fyi': {
    'builders': {
      'V8 - node.js integration - lkgr': {
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
})

ARCHIVE_LINK = ('https://storage.googleapis.com'
                '/chromium-v8/node-linux-rel/%s')


def _build_and_test(api, suffix=''):
  api.step(
    'configure node.js%s' % suffix,
    [api.path['slave_build'].join('node.js', 'configure')],
    cwd=api.path['slave_build'].join('node.js'),
  )

  api.step(
    'build and test node.js%s' % suffix,
    ['make', '-j8', 'test'],
    cwd=api.path['slave_build'].join('node.js'),
  )

def _build_and_upload(api):
  api.step(
    'configure node.js - install',
    [
      api.path['slave_build'].join('node.js', 'configure'),
      '--prefix=/',
      '--tag=v8-build-%s' % api.v8.revision,
    ],
    cwd=api.path['slave_build'].join('node.js'),
  )

  archive_dir = api.path['slave_build'].join('archive-build')
  archive_name = ('node-linux-rel-%s-%s.zip' %
                  (api.v8.revision_number, api.v8.revision))
  zip_file = api.path['slave_build'].join(archive_name)

  # Make archive directory.
  api.file.makedirs('install directory', archive_dir)

  # Build and install.
  api.step(
    'build and install node.js',
    ['make', '-j8', 'install', 'DESTDIR=%s' % archive_dir],
    cwd=api.path['slave_build'].join('node.js'),
  )

  # Zip build.
  package = api.zip.make_package(archive_dir, zip_file)
  package.add_directory(archive_dir)
  package.zip('zipping')

  # Upload to google storage bucket.
  api.gsutil.upload(
    zip_file,
    'chromium-v8/node-linux-rel',
    archive_name,
    args=['-a', 'public-read'],
  )

  api.step('Archive link', cmd=None)
  api.step.active_result.presentation.links['download'] = (
      ARCHIVE_LINK % archive_name)

  # Clean up.
  api.file.remove('cleanup archive', zip_file)
  api.file.rmtree('archive directory', archive_dir)


def RunSteps(api):
  v8 = api.v8
  v8.apply_bot_config(BUILDERS)
  api.gclient.apply_config('node_js')
  v8.checkout()
  api.chromium.cleanup_temp()

  try:
    # Build and test the node.js branch as FYI.
    _build_and_test(api, ' - baseline')
  except api.step.StepFailure:  # pragma: no cover
    pass

  # Copy the checked-out v8.
  api.file.rmtree('v8', api.path['slave_build'].join('node.js', 'deps', 'v8'))
  api.python(
      name='copy v8 tree',
      script=api.v8.resource('copy_v8.py'),
      args=[
        # Source.
        api.path['slave_build'].join('v8'),
        # Destination.
        api.path['slave_build'].join('node.js', 'deps', 'v8'),
        # Paths to ignore.
        '.git',
        api.path['slave_build'].join('v8', 'buildtools'),
        api.path['slave_build'].join('v8', 'out'),
        api.path['slave_build'].join('v8', 'third_party'),
      ],
  )

  # Build and test node.js with the checked-out v8.
  _build_and_test(api)

  # Build and upload node.js distribution with the checked-out v8.
  _build_and_upload(api)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, masterconf in BUILDERS.iteritems():
    for buildername, _ in masterconf['builders'].iteritems():
      yield (
          api.test('_'.join([
            'full',
            _sanitize_nonalpha(mastername),
            _sanitize_nonalpha(buildername),
          ])) +
          api.properties.generic(
              mastername=mastername,
              buildername=buildername,
              branch='refs/heads/lkgr',
              revision='deadbeef',
          )
      )
