# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test the deterministic build.

Waterfall page: https://build.chromium.org/p/chromium.swarm/waterfall

"""

from recipe_engine.recipe_api import Property
from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'chromium_android',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'isolate',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

DETERMINISTIC_BUILDERS = freeze({
  'Mac deterministic': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'platform': 'mac',
    'targets': ['all'],
  },
  'Windows deterministic': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'platform': 'win',
    'targets': ['all'],
  },

  # Debug builders
  'Mac deterministic (dbg)': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'platform': 'mac',
    'targets': ['all'],
  },

  'Deterministic Linux': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'platform': 'linux',
    'targets': ['all'],
  },
  'linux_chromium_clobber_deterministic': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'platform': 'linux',
    'targets': ['all'],
  },
  'Deterministic Linux (dbg)': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'platform': 'linux',
    'targets': ['all'],
    'compare_local': True,
  },
  'Deterministic Android': {
    'chromium_config': 'android',
    'android_config': 'main_builder',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
      'TARGET_PLATFORM': 'android',
    },
    'platform': 'linux',
    'targets': ['all'],
  },
  'Deterministic Android (dbg)': {
    'chromium_config': 'android',
    'android_config': 'main_builder',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Debug',
      'TARGET_BITS': 32,
      'TARGET_PLATFORM': 'android',
    },
    'platform': 'linux',
    'targets': ['all'],
  },
})

# Trybots to mirror the actions of builders
DETERMINISTIC_TRYBOTS = freeze({
  'android-deterministic-rel': 'Deterministic Android',
  'android-deterministic-dbg': 'Deterministic Android (dbg)',
})

def MoveBuildDirectory(api, src_dir, dst_dir):
  api.python.inline('Move %s to %s' % (src_dir, dst_dir),
                    """
                    import os
                    import shutil
                    import sys
                    if os.path.exists(sys.argv[2]):
                      shutil.rmtree(sys.argv[2])
                    shutil.move(sys.argv[1], sys.argv[2])""",
                    args=[src_dir, dst_dir])


def ConfigureChromiumBuilder(api, recipe_config):
  api.chromium.set_config(recipe_config['chromium_config'],
                          **recipe_config.get('chromium_config_kwargs',
                                              {'BUILD_CONFIG': 'Release'}))
  api.gclient.set_config(recipe_config['gclient_config'],
                         **recipe_config.get('gclient_config_kwargs', {}))

  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if recipe_config.get('android_config'):
    api.chromium_android.configure_from_properties(
        recipe_config.get('android_config'),
        **recipe_config.get('chromium_config_kwargs', {}))

  # Checkout chromium.
  api.bot_update.ensure_checkout()


PROPERTIES = {
  'buildername': Property(),
}


def RunSteps(api, buildername):
  if buildername in DETERMINISTIC_BUILDERS:
    recipe_config = DETERMINISTIC_BUILDERS[buildername]
  else:
    recipe_config = DETERMINISTIC_BUILDERS[DETERMINISTIC_TRYBOTS[buildername]]

  if recipe_config.get('chromium_config_kwargs'):
    target_platform = recipe_config['chromium_config_kwargs'].get(
        'TARGET_PLATFORM')
  else:
    target_platform = recipe_config.get('platform')

  # Set up a named cache so runhooks doesn't redownload everything on each run.
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)

  with api.context(cwd=solution_path):
    ConfigureChromiumBuilder(api, recipe_config)

  # The default setup by this recipe is to do a clobber build in one directory,
  # move it elsewhere, then do another clobber build in the original directory,
  # and then to compare the two directories. This doesn't check that
  # different build directories produce the same output, and it doesn't check
  # that incremental builds produce the same output as clobber builds.
  # If check_different_build_dirs is set, the recipe instead does an incremental
  # build in the usual build dir and a clobber build in a differently-named
  # build dir and then compares the outputs.
  # TODO(thakis): Do this on all platforms, https://crbug.com/899438
  check_different_build_dirs = target_platform in ['linux', 'win']

  # Since disk lacks in Mac, we need to remove files before build.
  # In check_different_build_dirs, only the .2 build dir exists here.
  for ext in '12':
    p = str(api.chromium.output_dir).rstrip('\\/') + '.' + ext
    api.file.rmtree('rmtree %s' % p, p)
  if check_different_build_dirs:
    # In this setup, one build dir does incremental builds. Make sure no stale
    # .isolate or .isolated hang around.
    api.file.rmglob('rm old .isolate', api.chromium.output_dir, '*.isolate')
    api.file.rmglob('rm old .isolated', api.chromium.output_dir, '*.isolated')

  targets = recipe_config['targets']

  api.chromium.ensure_goma()
  with api.context(cwd=solution_path):
    api.chromium.runhooks()

  # Whether do first build in local or use goma.
  compare_local = recipe_config.get('compare_local', False)

  # Do a first build and move the build artifact to the temp directory.
  api.chromium.mb_gen(api.properties.get('mastername'), buildername,
                      phase='local' if compare_local else None)
  api.chromium.mb_isolate_everything(api.properties.get('mastername'),
                                     buildername)

  api.chromium.compile(targets, name='First build',
                       use_goma_module=not compare_local)

  if not check_different_build_dirs:
    MoveBuildDirectory(api, str(api.chromium.output_dir),
                       str(api.chromium.output_dir).rstrip('\\/') + '.1')

  # Do the second build and move the build artifact to the temp directory.
  build_dir, target = None, None
  if check_different_build_dirs:
    build_dir = '//out/Release.2'
    target = 'Release.2'

  api.chromium.mb_gen(api.properties.get('mastername'), buildername,
                      build_dir=build_dir,
                      phase='goma' if compare_local else None)

  api.chromium.mb_isolate_everything(api.properties.get('mastername'),
                                     buildername, build_dir=build_dir)
  api.chromium.compile(targets, name='Second build', use_goma_module=True,
                       target=target)
  if not check_different_build_dirs:
    MoveBuildDirectory(api, str(api.chromium.output_dir),
                       str(api.chromium.output_dir).rstrip('\\/') + '.2')

  # Compare the artifacts from the 2 builds, raise an exception if they're
  # not equals.
  # TODO(sebmarchand): Do a smarter comparison.
  first_dir = str(api.chromium.output_dir)
  if not check_different_build_dirs:
    first_dir = first_dir.rstrip('\\/') + '.1'
  api.isolate.compare_build_artifacts(
      first_dir,
      str(api.chromium.output_dir).rstrip('\\/') + '.2')


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

def GenTests(api):
  mastername = 'chromium.swarm'
  for buildername in DETERMINISTIC_BUILDERS:
    test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                _sanitize_nonalpha(buildername))
    yield (
      api.test(test_name) +
      api.properties.scheduled() +
      api.properties.generic(buildername=buildername,
                             mastername=mastername) +
      api.platform(DETERMINISTIC_BUILDERS[buildername]['platform'], 32) +
      api.properties(configuration='Release')
    )
    yield (
      api.test(test_name + '_fail') +
      api.properties.scheduled() +
      api.properties.generic(buildername=buildername,
                             mastername=mastername) +
      api.platform(DETERMINISTIC_BUILDERS[buildername]['platform'], 32) +
      api.properties(configuration='Release') +
      api.step_data('compare_build_artifacts', retcode=1)
    )

  for trybotname in DETERMINISTIC_TRYBOTS:
    test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                _sanitize_nonalpha(trybotname))
    yield (
      api.test(test_name) +
      api.properties.scheduled() +
      api.properties.generic(buildername=trybotname,
                             mastername=mastername) +
      api.platform(DETERMINISTIC_BUILDERS[
          DETERMINISTIC_TRYBOTS[trybotname]]['platform'], 32) +
      api.properties(configuration='Release')
    )
    yield (
      api.test(test_name + '_fail') +
      api.properties.scheduled() +
      api.properties.generic(buildername=trybotname,
                              mastername=mastername) +
      api.platform(DETERMINISTIC_BUILDERS[
          DETERMINISTIC_TRYBOTS[trybotname]]['platform'], 32) +
      api.properties(configuration='Release') +
      api.step_data('compare_build_artifacts', retcode=1)
    )
