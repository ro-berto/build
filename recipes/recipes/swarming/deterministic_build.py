# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test the deterministic build.

Waterfall page: https://build.chromium.org/p/chromium.swarm/waterfall

"""

from recipe_engine import post_process
from recipe_engine.engine_types import freeze
from recipe_engine.recipe_api import Property
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium

DEPS = [
    'builder_group',
    'chromium',
    'chromium_android',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'reclient',
]

DETERMINISTIC_BUILDERS = freeze({
    'Mac deterministic': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'gclient_apply_config': ['enable_reclient'],
        'platform': 'mac',
        'targets': ['all'],
    },
    'Mac deterministic (reclient shadow)': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'platform': 'mac',
        'targets': ['all'],
        'gclient_apply_config': ['enable_reclient'],
    },
    'Windows deterministic': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'gclient_apply_config': ['enable_reclient'],
        'platform': 'win',
        'targets': ['all'],
    },

    # Debug builders
    'Mac deterministic (dbg)': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'gclient_apply_config': ['enable_reclient'],
        'platform': 'mac',
        'targets': ['all'],
    },
    'Deterministic Linux': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'gclient_apply_config': ['enable_reclient'],
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
        'chromium_config_kwargs': {
            'BUILD_CONFIG': 'Debug',
        },
        'gclient_config': 'chromium',
        'gclient_apply_config': ['enable_reclient'],
        'platform': 'linux',
        'targets': ['all'],
        'compare_local': True,
    },
    'Deterministic Android': {
        'chromium_config': 'android',
        'android_config': 'main_builder',
        'gclient_config': 'chromium',
        'gclient_apply_config': ['android', 'enable_reclient'],
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
        'gclient_apply_config': ['android', 'enable_reclient'],
        'chromium_config_kwargs': {
            'BUILD_CONFIG': 'Debug',
            'TARGET_BITS': 32,
            'TARGET_PLATFORM': 'android',
        },
        'platform': 'linux',
        'targets': ['all'],
    },
    'Deterministic Fuchsia (dbg)': {
        'chromium_config': 'chromium',
        'chromium_config_kwargs': {
            'BUILD_CONFIG': 'Debug',
            'TARGET_BITS': 64,
            'TARGET_PLATFORM': 'fuchsia',
        },
        'gclient_config': 'chromium',
        'gclient_apply_config': ['fuchsia_x64'],
        'platform': 'linux',
        'targets': ['all'],
    },
})

# Trybots to mirror the actions of builders
DETERMINISTIC_TRYBOTS = freeze({
    'android-deterministic-rel': 'Deterministic Android',
    'android-deterministic-dbg': 'Deterministic Android (dbg)',
    'fuchsia-deterministic-dbg': 'Deterministic Fuchsia (dbg)',
})

def MoveBuildDirectory(api, src_dir, dst_dir):
  cmd = ['python3', api.resource('move.py'), src_dir, dst_dir]
  api.step('Move %s to %s' % (src_dir, dst_dir), cmd)


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


def RunSteps(api):
  buildername = api.buildbucket.builder_name
  if buildername in DETERMINISTIC_BUILDERS:
    recipe_config = DETERMINISTIC_BUILDERS[buildername]
  else:
    recipe_config = DETERMINISTIC_BUILDERS[DETERMINISTIC_TRYBOTS[buildername]]

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
  check_different_build_dirs = (
      api.chromium.c.TARGET_PLATFORM in ['fuchsia', 'linux', 'win'])

  # Since disk lacks in Mac, we need to remove files before build.
  # In check_different_build_dirs, only the .2 build dir exists here.
  for ext in '12':
    p = str(api.chromium.output_dir).rstrip('\\/') + '.' + ext
    api.file.rmtree('rmtree %s' % p, p)
  if check_different_build_dirs:
    # In this setup, one build dir does incremental builds. Make sure no stale
    # .runtime_deps (explicitly also in subdirectories) files hang around.
    api.file.rmglob('rm old .runtime_deps', api.chromium.output_dir,
                    '**/*.runtime_deps')

  targets = recipe_config['targets']

  api.chromium.ensure_goma()
  with api.context(cwd=solution_path):
    api.chromium.runhooks()

  # Whether do first build in local or use goma.
  compare_local = recipe_config.get('compare_local', False)

  use_reclient = bool(api.reclient.instance)
  use_goma = not use_reclient
  remote_phase = 'goma' if use_goma else 'reclient'

  # Do a first build and move the build artifact to the temp directory.
  builder_id = chromium.BuilderId.create_for_group(
      api.builder_group.for_current, buildername)
  api.chromium.mb_gen(builder_id, phase='local' if compare_local else None)
  api.chromium.mb_isolate_everything(
      builder_id, phase='local' if compare_local else None)

  raw_result = api.chromium.compile(
      targets,
      name='First build',
      use_goma_module=use_goma and not compare_local,
      use_reclient=use_reclient and not compare_local)
  if raw_result.status != common_pb.SUCCESS:
    return raw_result

  if not check_different_build_dirs:
    MoveBuildDirectory(api, str(api.chromium.output_dir),
                       str(api.chromium.output_dir).rstrip('\\/') + '.1')

  # Do the second build and move the build artifact to the temp directory.
  build_dir, target = None, None
  if check_different_build_dirs:
    target = '%s.2' % api.chromium.c.build_config_fs
    build_dir = '//out/%s' % target

  api.chromium.mb_gen(
      builder_id,
      build_dir=build_dir,
      phase=remote_phase if compare_local else None)

  api.chromium.mb_isolate_everything(
      builder_id,
      build_dir=build_dir,
      phase=remote_phase if compare_local else None)
  raw_result = api.chromium.compile(
      targets,
      name='Second build',
      use_goma_module=use_goma,
      use_reclient=use_reclient,
      target=target)
  if raw_result.status != common_pb.SUCCESS:
    return raw_result

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
  builder_group = 'chromium.swarm'
  for buildername in DETERMINISTIC_BUILDERS:
    test_name = 'full_%s_%s' % (_sanitize_nonalpha(builder_group),
                                _sanitize_nonalpha(buildername))
    yield api.test(
        test_name,
        api.chromium.ci_build(builder_group=builder_group, builder=buildername),
        api.platform(DETERMINISTIC_BUILDERS[buildername]['platform'], 64),
        api.properties(
            buildername=buildername, buildnumber=571, configuration='Release'),
    )
    yield api.test(
        test_name + '_fail',
        api.chromium.ci_build(builder_group=builder_group, builder=buildername),
        api.platform(DETERMINISTIC_BUILDERS[buildername]['platform'], 64),
        api.properties(
            buildername=buildername, buildnumber=571, configuration='Release'),
        api.step_data('compare_build_artifacts', retcode=1),
    )

  for trybotname in DETERMINISTIC_TRYBOTS:
    test_name = 'full_%s_%s' % (_sanitize_nonalpha(builder_group),
                                _sanitize_nonalpha(trybotname))
    yield api.test(
        test_name,
        api.chromium.try_build(builder_group=builder_group, builder=trybotname),
        api.properties(buildername=trybotname, buildnumber=571),
        api.platform(
            DETERMINISTIC_BUILDERS[DETERMINISTIC_TRYBOTS[trybotname]]
            ['platform'], 64),
        api.properties(configuration='Release'),
    )
    yield api.test(
        test_name + '_fail',
        api.chromium.try_build(builder_group=builder_group, builder=trybotname),
        api.properties(buildername=trybotname, buildnumber=571),
        api.platform(
            DETERMINISTIC_BUILDERS[DETERMINISTIC_TRYBOTS[trybotname]]
            ['platform'], 64),
        api.properties(configuration='Release'),
        api.step_data('compare_build_artifacts', retcode=1),
    )

  yield api.test(
      'first_build_compile_fail',
      api.chromium.ci_build(
          builder_group=builder_group, builder='android-deterministic-dbg'),
      api.properties(buildername='android-deterministic-dbg', buildnumber=571),
      api.platform(
          DETERMINISTIC_BUILDERS['Deterministic Android (dbg)']['platform'],
          64),
      api.properties(configuration='Release'),
      api.step_data('First build', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'second_build_compile_fail',
      api.chromium.ci_build(
          builder_group=builder_group, builder='android-deterministic-dbg'),
      api.properties(buildername='android-deterministic-dbg', buildnumber=571),
      api.platform(
          DETERMINISTIC_BUILDERS['Deterministic Android (dbg)']['platform'],
          64),
      api.properties(configuration='Release'),
      api.step_data('Second build', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
