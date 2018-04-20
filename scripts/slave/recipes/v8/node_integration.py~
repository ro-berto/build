# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test v8/node.js integration."""

from recipe_engine.types import freeze


DEPS = [
  'chromium',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'trigger',
  'v8',
  'zip',
]

BUILDERS = freeze({
  'client.v8.fyi': {
    'builders': {
      'V8 - node.js baseline': {
        'baseline_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'V8 - node.js integration': {
        'triggers': [
          'v8_node_linux64_haswell_perf',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'tryserver.v8': {
    'builders': {
      'v8_node_linux64_rel': {
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
  with api.context(cwd=api.v8.checkout_root.join('node.js')):
    api.step(
      'configure node.js%s' % suffix,
      [api.v8.checkout_root.join('node.js', 'configure')],
    )

    api.step(
      'build node.js%s' % suffix,
      ['make', '-j8'],
    )

    api.step(
      'build addons and test node.js%s' % suffix,
      ['make', '-j8', 'test-ci'],
    )

def _build_and_upload(api):
  with api.context(cwd=api.v8.checkout_root.join('node.js')):
    api.step(
      'configure node.js - install',
      [
        api.v8.checkout_root.join('node.js', 'configure'),
        '--prefix=/',
        '--tag=v8-build-%s' % api.v8.revision,
      ],
    )

  # TODO(machenbach): Use a proper temp dir for putting archive-build and the
  # zip file to not depend on start_dir.
  archive_dir = api.path['start_dir'].join('archive-build')
  archive_name = ('node-linux-rel-%s-%s.zip' %
                  (api.v8.revision_number, api.v8.revision))
  zip_file = api.path['start_dir'].join(archive_name)

  # Make archive directory.
  api.file.ensure_directory('install directory', archive_dir)

  # Build and install.
  with api.context(cwd=api.v8.checkout_root.join('node.js')):
    api.step(
      'build and install node.js',
      ['make', '-j8', 'install', 'DESTDIR=%s' % archive_dir],
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

  if v8.bot_config.get('baseline_only', False):
    _build_and_test(api)
    return

  args = [
    api.v8.checkout_root.join('v8'),
    api.v8.checkout_root.join('node.js'),
  ]

  if api.tryserver.is_tryserver:
    args.append('--with-patch')

  # Update V8.
  api.python(
      name='update v8',
      script=api.v8.checkout_root.join(
          'v8', 'tools', 'release', 'update_node.py'),
      args=args,
  )

  # Build and test node.js with the checked-out v8.
  _build_and_test(api)

  # Don't upload on tryserver.
  if api.tryserver.is_tryserver:
    return

  # Build and upload node.js distribution with the checked-out v8.
  _build_and_upload(api)

  # Trigger performance bots.
  api.trigger(*[{
    'builder_name': builder_name,
    'bucket': 'master.internal.client.v8',
    'properties': {
      'revision': api.v8.revision,
      'parent_got_revision': api.v8.revision,
      'parent_got_revision_cp': api.v8.revision_cp,
    },
    'buildbot_changes': [{
      'author': 'node.js',
      'revision': api.v8.revision,
    }]
  } for builder_name in api.v8.bot_config['triggers']])


def _sanitize_nonalpha(*chunks):
  return '_'.join(
      ''.join(c if c.isalnum() else '_' for c in text)
      for text in chunks
  )


def GenTests(api):
  for mastername, masterconf in BUILDERS.iteritems():
    for buildername, _ in masterconf['builders'].iteritems():
      if mastername.startswith('tryserver'):
        properties_fn = api.properties.tryserver
      else:
        properties_fn = api.properties.generic
      yield (
          api.test(_sanitize_nonalpha('full', mastername, buildername)) +
          properties_fn(
              mastername=mastername,
              buildername=buildername,
              branch='refs/heads/master',
              revision='deadbeef',
          )
      )
