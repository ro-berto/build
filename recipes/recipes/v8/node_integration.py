# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test v8/node.js integration."""

import six

from contextlib import contextmanager

from recipe_engine.engine_types import freeze
from recipe_engine.post_process import Filter


PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'depot_tools/gclient',
    'depot_tools/gsutil',
    'depot_tools/tryserver',
    'goma',
    'infra/zip',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'v8',
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
          'v8_node_linux64_perf',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'V8 Linux64 debug - node.js baseline': {
        'baseline_only': True,
        'is_debug': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'V8 Linux64 debug - node.js integration': {
        'is_debug': True,
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

# TODO(machenbach): Temporary code to migrate to flattened builder configs.
# Clean up the config above and remove this after testing in prod.
FLATTENED_BUILDERS = {}
for _, group_config in six.iteritems(BUILDERS):
  builders = group_config['builders']
  for _buildername, _bot_config in six.iteritems(builders):
    assert _buildername not in FLATTENED_BUILDERS, _buildername
    FLATTENED_BUILDERS[_buildername] = _bot_config
FLATTENED_BUILDERS = freeze(FLATTENED_BUILDERS)

ARCHIVE_LINK = ('https://storage.googleapis.com'
                '/chromium-v8/experimental/node-%s-rel/%s')


@contextmanager
def goma_wrapper(api):
  api.goma.start()
  try:
    yield
    api.goma.stop(build_exit_status=0)
  except api.step.StepFailure as e: # pragma: no cover
    api.goma.stop(build_exit_status=e.retcode)
    raise


def _run_make(api, step_name, args):
  make_mode_args = []
  if api.v8.bot_config.get('is_debug', False):
    make_mode_args = ['BUILDTYPE=Debug']
  api.step(
      step_name,
      ['make'] + make_mode_args + args,
  )

def _build_and_test(api, goma_dir):
  with api.context(cwd=api.v8.checkout_root.join('node.js')):
    with api.step.nest('build'):
      args = [
        '--build-v8-with-gn',
        '--build-v8-with-gn-max-jobs=%d' % api.goma.recommended_goma_jobs,
        '--build-v8-with-gn-extra-gn-args',
        'use_goma=true goma_dir="%s"' % goma_dir,
      ]

      build_config = 'Release'
      if api.v8.bot_config.get('is_debug', False):
        args.append('--debug')
        build_config = 'Debug'

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

      with goma_wrapper(api):
        if api.platform.is_win:
          # TODO(machenbach): Figure out what to do with clear-stalled and
          # addons.
          api.step(
            'build node.js',
            ['ninja', '-C', api.path.join('out', build_config)],
          )
        else:
          _run_make(api, 'build node.js', ['-j8'])
          _run_make(api, 'clean addons', ['test-addons-clean'])

          # TODO(machenbach): This contains all targets test-ci depends on.
          # Migrate this to ninja.
          _run_make(api, 'clear stalled', ['-j8', 'clear-stalled'])
          _run_make(api, 'build addons', ['-j8', 'build-addons'])
          _run_make(api, 'build addons-napi', ['-j8', 'build-addons-napi'])
          _run_make(api, 'build doc-only', ['-j8', 'doc-only'])

    api.step(
      'run cctest',
      [
        api.path.join('out', build_config, 'cctest'),
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
        '--mode=%s' % build_config.lower(),
        '--flaky-tests', 'run',
      ] + suites,
    )

def _build_and_upload(api, goma_dir):
  with api.step.nest('build and upload') as parent:
    with api.context(cwd=api.v8.checkout_root.join('node.js')):
      api.python(
        name='configure node.js - install',
        script=api.v8.checkout_root.join('node.js', 'configure'),
        args=[
          '--prefix=/',
          '--tag=v8-build-%s' % api.v8.revision,
          '--build-v8-with-gn',
          '--build-v8-with-gn-max-jobs=%d' % api.goma.recommended_goma_jobs,
          '--build-v8-with-gn-extra-gn-args',
          'use_goma=true goma_dir="%s"' % goma_dir,
        ],
      )

    archive_dir = api.path['cleanup'].join('archive-build')
    archive_name = ('node-%s-rel-%s-%s.zip' %
                    (api.platform.name, api.v8.revision_number,
                     api.v8.revision))
    parent.presentation.links['download'] = (
        ARCHIVE_LINK % (api.platform.name, archive_name))
    zip_file = api.path['cleanup'].join(archive_name)

    # Make archive directory.
    api.file.ensure_directory('install directory', archive_dir)

    # Build and install.
    with goma_wrapper(api):
      with api.context(cwd=api.v8.checkout_root.join('node.js')):
        _run_make(
            api, 'build and install node.js',
            ['-j8', 'install', 'DESTDIR=%s' % archive_dir],
        )

    # Zip build.
    package = api.zip.make_package(archive_dir, zip_file)
    package.add_file(archive_dir.join('bin', 'node'))
    package.zip('zipping')

    # Upload to google storage bucket.
    api.gsutil.upload(
      zip_file,
      'chromium-v8/experimental/node-%s-rel' % api.platform.name,
      archive_name,
      args=['-a', 'public-read'],
    )


def RunSteps(api):
  v8 = api.v8
  v8.apply_bot_config(v8.bot_config_by_buildername(
      builders=FLATTENED_BUILDERS, use_goma=True))
  # Opt out of using gyp environment variables.
  api.chromium.c.use_gyp_env = False
  api.gclient.apply_config('node_js')

  with api.step.nest('initialization'):
    v8.checkout()
    v8.runhooks()
    goma_dir = api.goma.ensure_goma()

  if v8.bot_config.get('baseline_only', False):
    _build_and_test(api, goma_dir)
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
  _build_and_test(api, goma_dir)

  # Don't upload on tryserver or on debug bots.
  if api.tryserver.is_tryserver or api.v8.bot_config.get('is_debug', False):
    return

  # Build and upload node.js distribution with the checked-out v8.
  if not api.platform.is_win:
    _build_and_upload(api, goma_dir)


def _sanitize_nonalpha(*chunks):
  return '_'.join(
      ''.join(c if c.isalnum() else '_' for c in text)
      for text in chunks
  )


def GenTests(api):
  for group, group_cfg in six.iteritems(BUILDERS):
    for buildername, bot_config in six.iteritems(group_cfg['builders']):
      buildbucket_kwargs = {
          'builder_group':
              group,
          'project':
              'v8',
          'git_repo':
              'https://chromium.googlesource.com/v8/v8',
          'builder':
              buildername,
          'build_number':
              571,
          'revision':
              'a' * 40,
          'tags':
              api.buildbucket.tags(
                  buildset='commit/gitiles/chromium.googlesource.com/v8/v8/+/'
                  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
      }
      if group.startswith('tryserver'):
        buildbucket_fn = api.chromium.try_build
        buildbucket_kwargs['change_number'] = 456789
        buildbucket_kwargs['patch_set'] = 12
      else:
        buildbucket_fn = api.chromium.ci_build
      yield api.test(
          _sanitize_nonalpha('full', group, buildername),
          buildbucket_fn(**buildbucket_kwargs),
          api.platform(bot_config['testing']['platform'], 64),
          api.v8.hide_infra_steps(),
      )
