# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import json

from recipe_engine.config import Dict
from recipe_engine.config import List
from recipe_engine.config import Single
from recipe_engine.post_process import (DoesNotRun, DropExpectation, MustRun,
                                        StepCommandContains, StatusSuccess)
from recipe_engine.recipe_api import Property

from PB.recipes.build.findit.chromium.single_revision import InputProperties

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/tryserver',
    'filter',
    'findit',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'test_utils',
]

PROPERTIES = InputProperties


def RunSteps(api, properties):

  # 0. Validate properties.
  assert (
      properties.target_builder and properties.target_builder.master and
      properties.target_builder.builder), 'Target builder property is required'
  # test_override_builders should not be set except when testing.
  assert not properties.test_override_builders or api._test_data.enabled

  # 1. Configure the builder.
  bot_id, bot_config, compile_kwargs = _configure_builder(
      api, properties.target_builder, properties.test_override_builders)

  # 2. Check out the code.
  bot_update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)

  # 3. Configure swarming
  api.chromium_swarming.configure_swarming('chromium', precommit=False)

  # 4. Determine what to build and what to test.
  compile_targets, test_objects = _compute_targets_and_tests(
      api, bot_config, bot_db, bot_id, properties.tests,
      properties.compile_targets, properties.skip_analyze)

  # 5. Build what's needed.
  if compile_targets:
    api.chromium_tests.compile_specific_targets(
        bot_config,
        bot_update_step,
        bot_db,
        compile_targets,
        tests_including_triggered=test_objects,
        **compile_kwargs)

  # 6. Run the tests.
  _run_tests(api, bot_config, test_objects, properties.tests,
             properties.test_repeat_count)


def _configure_builder(api, target_builder, test_override_builders):
  if test_override_builders:
    builders = json.loads(test_override_builders)
  else:
    builders = api.chromium_tests.builders

  target_mastername = target_builder.master
  target_testername = target_builder.builder
  tester_config = builders[target_mastername].get('builders', {}).get(
      target_testername, {})
  target_buildername = (
      tester_config.get('parent_buildername') or target_testername)
  bot_id = api.chromium_tests.create_bot_id(
      target_mastername, target_buildername, target_testername)
  bot_config = api.chromium_tests.create_bot_config_object([bot_id])
  api.chromium_tests.configure_build(
      bot_config, override_bot_type='builder_tester')

  # If there is a problem with goma, rather than default to compiling locally
  # only, fail. This is important because findit relies on fast compile for
  # timely production of actionable changes, and local compilation alone is
  # unlikely to help findit find a culprit in time for automatic revert.
  # Better to fail the analysis and let the sheriffs try to find a culprit
  # manually.
  api.chromium.apply_config('goma_failfast')

  if target_buildername != target_testername:
    for key, value in tester_config.get('swarming_dimensions', {}).iteritems():
      # Coercing str as json.loads creates unicode strings. This only matters
      # for testing.
      api.chromium_swarming.set_default_dimension(str(key), str(value))

  compile_kwargs = {
      'mb_mastername': target_mastername,
      'mb_buildername': target_buildername,
      'override_bot_type': 'builder_tester',
  }
  return bot_id, bot_config, compile_kwargs


def _compute_targets_and_tests(api, bot_config, bot_db, bot_id, requested_tests,
                               compile_targets, skip_analyze):
  test_config = api.chromium_tests.get_tests(bot_config, bot_db)
  if requested_tests:
    # Figure out which test steps to run.
    requested_tests_to_run = [
        test for test in test_config.all_tests()
        if test.canonical_name in requested_tests
    ]

    # Figure out the test targets to be compiled.
    requested_test_targets = []
    for test in requested_tests_to_run:
      requested_test_targets.extend(test.compile_targets())
    requested_test_targets = sorted(set(requested_test_targets))

    if skip_analyze:
      # All test targets requested
      return requested_test_targets, requested_tests_to_run

    # '' is src/ relative to src/
    changed_files = api.tryserver.get_files_affected_by_patch('')

    affected_test_targets, actual_compile_targets = (
        api.filter.analyze(
            changed_files,
            test_targets=tuple(requested_test_targets),
            additional_compile_targets=tuple(compile_targets),
            config_file_name='trybot_analyze_config.json',
            mb_mastername=bot_id['mastername'],
            mb_buildername=bot_id['buildername']))

    actual_tests_to_run = []
    for test in requested_tests_to_run:
      targets = test.compile_targets()
      if targets and not any(t in affected_test_targets for t in targets):
        # Skip tests whose targets are not affected by the change.
        # NB: Non-compiled tests i.e. checkperms are not filtered out.
        continue
      actual_tests_to_run.append(test)
    # Targets filtered by analyze
    return actual_compile_targets, actual_tests_to_run

  # No tests, only compile targets
  default_compile_targets = api.chromium_tests.get_compile_targets(
      bot_config, bot_db, test_config.all_tests())
  # If no targets were specifically requested, compile every target in the spec.
  if not compile_targets:
    return default_compile_targets, []
  # Compile _requested_ targets that _are_ defined in the spec. To avoid trying
  # to compile targets that do not exist at this revision.
  return [t for t in default_compile_targets if t in compile_targets ], []


def _run_tests(api, bot_config, test_objects, requested_tests,
               test_repeat_count):
  # Default to 20 repeats.
  test_repeat_count = test_repeat_count or 20
  # test_objects are instances of the classes under chromium_tests/steps
  # whereas requested_tests is the dictionary passed as a property mapping a
  # test step to the test names to run.
  for test_obj in test_objects:
    test_filter = tuple(requested_tests[test_obj.canonical_name].names)
    # ScriptTests do not support test_options property
    if not isinstance(test_obj, api.chromium_tests.steps.ScriptTest):
      test_obj.test_options = api.chromium_tests.steps.TestOptions(
          test_filter=test_filter,
          repeat_count=test_repeat_count,
          retry_limit=0 if test_repeat_count else None,
          run_disabled=bool(test_repeat_count))

  # Run the tests.
  with api.chromium_tests.wrap_chromium_tests(bot_config, test_objects):
    return api.test_utils.run_tests(api.chromium_tests.m, test_objects, '')


def GenTests(api):

  def _StepCommandNotContains(check, step_odict, step, arg):
    check('Step %s does not contain %s' % (step, arg),
          arg not in step_odict[step].cmd)

  def _common(api, test_repeat_count=20, target_master='chromium.linux',
              target_builder='Linux Builder', tests=None, compile_targets=None,
              test_override_builders=False, spec=None, skip_analyze=False):
    """Create test properties and other data for tests."""
    tests = tests or {}
    compile_targets = compile_targets or []
    _default_spec = 'chromium.linux', {
        'Linux Builder': {
            'isolated_scripts': [{
                'isolate_name': 'blink_web_tests',
                'name': 'blink_web_tests',
                'swarming': {
                    'can_use_on_swarming_builders': True,
                    'shards': 1,
                },
            }],
            'gtest_tests': [{
                'test': 'base_unittests',
                'swarming': {
                    'can_use_on_swarming_builders': True
                },
            }],
        }
    }
    _default_builders = json.dumps({
        'chromium.linux': {
            'builders': {
                'Linux Tests': {
                    'parent_buildername': 'Linux Builder',
                    'swarming_dimensions': {
                        'pool': 'luci.dummy.pool'
                    },
                    'chromium_config': 'chromium',
                    'chromium_apply_config': ['mb'],
                    'gclient_config': 'chromium',
                    'chromium_config_kwargs': {
                        'BUILD_CONFIG': 'Release',
                        'TARGET_BITS': 64,
                    },
                    'bot_type': 'tester',
                    'testing': {
                        'platform': 'linux'
                    },
                },
                'Linux Builder': {
                    'swarming_dimensions': {
                        'pool': 'luci.dummy.pool'
                    },
                    'chromium_config': 'chromium',
                    'chromium_apply_config': ['mb'],
                    'gclient_config': 'chromium',
                    'chromium_config_kwargs': {
                        'BUILD_CONFIG': 'Release',
                        'TARGET_BITS': 64,
                    },
                    'bot_type': 'builder',
                    'testing': {
                        'platform': 'linux'
                    },
                }
            }
        }
    })

    props_proto = InputProperties()
    props_proto.skip_analyze = skip_analyze
    props_proto.test_repeat_count = test_repeat_count
    props_proto.target_builder.master = target_master
    props_proto.target_builder.builder = target_builder
    for t in compile_targets:
      props_proto.compile_targets.append(t)
    for k, v in tests.iteritems():
      new_message = props_proto.tests[k]
      for t in v:
        new_message.names.append(t)
    if test_override_builders:
      props_proto.test_override_builders = _default_builders
    return (
        api.properties(props_proto)
        + api.properties.generic(
            mastername=target_master,
            buildername=target_builder)
        + api.buildbucket.ci_build(
            project='chromium/src',
            builder=target_builder)
        + api.chromium_tests.read_source_side_spec(*(spec or _default_spec))
    )

  yield (
      api.test('all_targets')
      + _common(api)
      + api.post_process(MustRun, 'compile')
      + api.post_process(StepCommandContains, 'compile', ['blink_web_tests'])
      + api.post_process(StepCommandContains, 'compile', ['base_unittests'])
      + api.post_process(StatusSuccess)
      + api.post_process(DropExpectation)
  )

  yield (
      api.test('specific_target')
      + _common(api, compile_targets=['base_unittests', 'missing_target'])
      + api.post_process(MustRun, 'compile')
      + api.post_process(StepCommandContains, 'compile', ['base_unittests'])
      + api.post_process(_StepCommandNotContains, 'compile', 'missing_target')
      + api.post_process(StatusSuccess)
      + api.post_process(DropExpectation)
  )

  yield (
      api.test('with_tests')
      + _common(
          api,
          skip_analyze=True,
          tests={
              'blink_web_tests': [
                  'fast/Test/One.html', 'fast/Test/Two.html', 'dummy/Three.js'],
              'base_unittests': []
        })
      + api.post_process(MustRun, 'compile')
      + api.post_process(MustRun, 'test_pre_run.[trigger] blink_web_tests')
      + api.post_process(
          StepCommandContains,
          'test_pre_run.[trigger] blink_web_tests',
          ['--gtest_filter='
           'fast/Test/One.html:fast/Test/Two.html:dummy/Three.js'])
      + api.post_process(MustRun, 'test_pre_run.[trigger] base_unittests')
      + api.post_process(DoesNotRun, 'analyze')
      + api.post_process(StatusSuccess)
      + api.post_process(DropExpectation)
  )

  yield (
      api.test('with_tests_and_analyze')
      + _common(
          api,
          test_override_builders=True,
          target_builder='Linux Tests',
          tests={
              'blink_web_tests': [
                'fast/Test/One.html', 'fast/Test/Two.html', 'dummy/Three.js'],
              'base_unittests': [],
          })
      + api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['base_unittests'],
              'test_targets': ['base_unittests'],
          }))
      + api.post_process(MustRun, 'compile')
      + api.post_process(DoesNotRun, 'test_pre_run.[trigger] blink_web_tests')
      + api.post_process(MustRun, 'test_pre_run.[trigger] base_unittests')
      + api.post_process(MustRun, 'analyze')
      + api.post_process(StatusSuccess)
      + api.post_process(DropExpectation)
  )

  yield (
      api.test('compile_skipped')
      + _common(
          api,
          tests={'checkperms': []},
          spec=('chromium.linux', {
              'Linux Builder': {
                  'scripts': [{
                      'name': 'checkperms',
                      'script': 'checkperms.py'
                  }]
              }
          }),
      )
      + api.post_process(DoesNotRun, 'compile')
      + api.post_process(MustRun, 'checkperms')
      + api.post_process(StatusSuccess)
      + api.post_process(DropExpectation)
  )
