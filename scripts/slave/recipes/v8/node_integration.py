# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test v8/node.js integration."""

from contextlib import contextmanager

from recipe_engine.types import freeze


DEPS = [
  'chromium',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'goma',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'trigger',
  'v8',
  'zip',
]

BUILDERS = freeze({
  'client.v8.fyi': {
    'builders': {
      'V8 Linux64 - node.js baseline': {
        'baseline_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'V8 Linux64 - node.js integration': {
        'triggers': [
          'v8_node_linux64_haswell_perf',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'V8 Win64 - node.js baseline': {
        'baseline_only': True,
        'testing': {
          'platform': 'win',
        },
      },
      'V8 Win64 - node.js integration': {
        'testing': {
          'platform': 'win',
        },
      },
      'V8 Mac64 - node.js baseline': {
        'baseline_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'V8 Mac64 - node.js integration': {
        'testing': {
          'platform': 'mac',
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
                '/chromium-v8/node-%s-rel/%s')


@contextmanager
def goma_wrapper(api, use_goma):
  if not use_goma:
    yield
    return

  api.goma.start()
  try:
    yield
  finally:
    api.goma.stop()


def _build_and_test(api, use_goma=False):
  with api.context(cwd=api.v8.checkout_root.join('node.js')):
    if use_goma:
      api.goma.ensure_goma()

    # TODO(machenbach): Add goma flags to configure.
    args = ['--build-v8-with-gn']
    env = {}
    if api.platform.is_win:
      # TODO(machenbach): Also switch other platforms to ninja eventually.
      # TODO(machenbach): Also linux/mac should be built with either all clang
      # or all gcc. Currently, the node.js part is built with gcc, while v8 is
      # built with clang.
      args += ['--ninja', '--use-clang-cl']
      # Configure script sets this to 0 by default.
      env['DEPOT_TOOLS_WIN_TOOLCHAIN'] = '1'
    with api.context(env=env):
      api.python(
        name='configure node.js',
        script=api.v8.checkout_root.join('node.js', 'configure'),
        args=args,
      )

    with goma_wrapper(api, use_goma):
      if api.platform.is_win:
        # TODO(machenbach): Figure out what to do with clear-stalled and addons.
        api.step(
          'build node.js',
          ['ninja', '-C', api.path.join('out', 'Release')],
        )
      else:
        api.step(
          'build node.js',
          ['make', '-j8'],
        )

        # TODO(machenbach): This contains all targets test-ci depends on.
        # Split this further up and migrate to ninja.
        api.step(
          'build addons',
          [
            'make', '-j8',
            'clear-stalled',
            'build-addons',
            'build-addons-napi',
            'doc-only',
          ],
        )

    api.step(
      'run cctest',
      [
        api.path.join('out', 'Release', 'cctest'),
      ],
    )

    suites = ['default']
    if not api.platform.is_win:
      # TODO(machenbach): Add those suites on windows once they are built.
      suites += [
        'addons',
        'addons-napi',
        'doctool',
      ]

    api.python(
      name='run tests',
      script=api.v8.checkout_root.join('node.js', 'tools', 'test.py'),
      args=[
        '-p', 'tap',
        '-j8',
        '--mode=release',
        '--flaky-tests', 'run',
      ] + suites,
    )

def _build_and_upload(api):
  with api.context(cwd=api.v8.checkout_root.join('node.js')):
    api.python(
      name='configure node.js - install',
      script=api.v8.checkout_root.join('node.js', 'configure'),
      args=[
        '--prefix=/',
        '--tag=v8-build-%s' % api.v8.revision,
        '--build-v8-with-gn',
      ],
    )

  archive_dir = api.path['cleanup'].join('archive-build')
  archive_name = ('node-%s-rel-%s-%s.zip' %
                  (api.platform.name, api.v8.revision_number, api.v8.revision))
  zip_file = api.path['cleanup'].join(archive_name)

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
  if api.runtime.is_experimental:
    api.step('fake upload to GS', cmd=None)
  else:
    api.gsutil.upload(
      zip_file,
      'chromium-v8/node-%s-rel' % api.platform.name,
      archive_name,
      args=['-a', 'public-read'],
    )

  api.step('Archive link', cmd=None)
  api.step.active_result.presentation.links['download'] = (
      ARCHIVE_LINK % (api.platform.name, archive_name))


def RunSteps(api):
  v8 = api.v8
  v8.apply_bot_config(BUILDERS)
  # Opt out of using gyp environment variables.
  api.chromium.c.use_gyp_env = False
  api.gclient.apply_config('node_js')
  v8.checkout()
  v8.runhooks()

  if v8.bot_config.get('baseline_only', False):
    _build_and_test(api, use_goma=True)
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
          'v8', 'tools', 'node', 'update_node.py'),
      args=args,
  )

  # Build and test node.js with the checked-out v8.
  _build_and_test(api)

  # Don't upload on tryserver.
  if api.tryserver.is_tryserver:
    return

  # Build and upload node.js distribution with the checked-out v8.
  if not api.platform.is_win:
    _build_and_upload(api)

  # Trigger performance bots.
  if api.v8.bot_config.get('triggers'):
    if api.runtime.is_experimental:
      # TODO(sergiyb): Replace this with a trigger to corresponding LUCI builder
      # once it's configured.
      api.step('fake trigger', cmd=None)
    else:
      api.v8.buildbucket_trigger(
          'master.internal.client.v8',
          api.v8.get_changes(),
          [
            {
              'properties': {
                'revision': api.v8.revision,
                'parent_got_revision': api.v8.revision,
                'parent_got_revision_cp': api.v8.revision_cp,
              },
              'builder_name': builder_name,
            } for builder_name in api.v8.bot_config['triggers']
          ]
      )


def _sanitize_nonalpha(*chunks):
  return '_'.join(
      ''.join(c if c.isalnum() else '_' for c in text)
      for text in chunks
  )


def GenTests(api):
  for mastername, masterconf in BUILDERS.iteritems():
    for buildername, bot_config in masterconf['builders'].iteritems():
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
          ) +
          api.platform(bot_config['testing']['platform'], 64)
      )

  yield (
    api.test('experimental') +
    api.properties.generic(
      mastername='client.v8.fyi',
      buildername='V8 Linux64 - node.js integration',
      branch='refs/heads/master',
      revision='deadbeef',
    ) +
    api.runtime(is_luci=True, is_experimental=True) +
    api.platform('linux', 64)
  )

