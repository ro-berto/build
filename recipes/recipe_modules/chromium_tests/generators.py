# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import collections
import json
import string
import textwrap

from . import steps

from recipe_engine import engine_types

from RECIPE_MODULES.build import chromium_swarming


def get_args_for_test(chromium_tests_api, raw_test_spec, bot_update_step):
  """Gets the argument list for a dynamically generated test, as
  provided by the JSON files in src/testing/buildbot/ in the Chromium
  workspace. This function provides the following build properties in
  the form of variable substitutions in the tests' argument lists:

      buildbucket_project
      buildbucket_build_id
      builder_group
      buildername
      buildnumber
      got_cr_revision
      got_revision
      got_src_revision
      patch_issue
      patch_set
      xcode_build_version

  so, for example, a test can declare the argument:

      --test-machine-name=\"${buildername}\"

  and ${buildername} will be replaced with the associated build
  property. In this example, it will also be double-quoted, to handle
  the case where the machine name contains contains spaces.

  This function also supports trybot-only and waterfall-only
  arguments, so that a test can pass a different argument lists on the
  continuous builders compared to tryjobs. This is useful when the
  waterfall bots generate some reference data that is tested against
  during tryjobs.

  This function also supports more general conditional arguments, where
  one of the substitution variables and a target value is specified. If
  the value of that variable is equal to the target value, then the
  associated arguments are added.
  """

  args = list(raw_test_spec.get('args', []))
  if chromium_tests_api.m.tryserver.is_tryserver:
    args.extend(raw_test_spec.get('precommit_args', []))
  else:
    args.extend(raw_test_spec.get('non_precommit_args', []))

  # Perform substitution of known variables.
  build = chromium_tests_api.m.buildbucket.build
  cl = (build.input.gerrit_changes or [None])[0]
  substitutions = {
      'buildbucket_project':
          build.builder.project,
      'buildbucket_build_id':
          build.id,
      'builder_group':
          chromium_tests_api.m.builder_group.for_current,
      'buildername':
          build.builder.builder,
      'buildnumber':
          build.number,
      # This is only set on Chromium when using ANGLE as a component. We
      # use the parent revision when available.
      'got_angle_revision':
          bot_update_step.presentation.properties.get(
              'parent_got_angle_revision',
              bot_update_step.presentation.properties.get('got_angle_revision')
          ),
      # This is only ever set on builders where the primary repo is not
      # Chromium, such as V8 or WebRTC.
      'got_cr_revision':
          bot_update_step.presentation.properties.get('got_cr_revision'),
      'got_revision': (bot_update_step.presentation.properties.get(
          'got_revision',
          bot_update_step.presentation.properties.get('got_src_revision'))),
      # Similar to got_cr_revision, but for use in repos where the primary
      # repo is not Chromium and got_cr_revision is not defined.
      'got_src_revision':
          bot_update_step.presentation.properties.get('got_src_revision'),
      'patch_issue':
          cl.change if cl else None,
      'patch_set':
          cl.patchset if cl else None,
      'xcode_build_version':
          chromium_tests_api.m.chromium.xcode_build_version
  }

  for conditional in raw_test_spec.get('conditional_args', []):

    def get_variable():
      if 'variable' not in conditional:
        error_message = "Conditional has no 'variable' key"
      else:
        variable = conditional['variable']
        if variable in substitutions:
          return substitutions[variable]
        error_message = "Unknown variable '{}'".format(conditional['variable'])
      chromium_tests_api.m.python.infra_failing_step(
          'Invalid conditional',
          'Test spec has invalid conditional: {}\n{}'.format(
              error_message,
              json.dumps(engine_types.thaw(raw_test_spec), indent=2),
          ))

    variable = get_variable()
    value = conditional.get('value', '')
    if (variable == value) == (not conditional.get('invert', False)):
      args.extend(conditional.get('args', []))

  return [string.Template(arg).safe_substitute(substitutions) for arg in args]


def _normalize_optional_dimensions(optional_dimensions):
  if not optional_dimensions:
    return optional_dimensions

  normalized = {}
  for expiration, dimensions_sequence in optional_dimensions.iteritems():
    if isinstance(dimensions_sequence, collections.Mapping):
      dimensions = dimensions_sequence
    else:
      # TODO(https://crbug.com/1148971): Convert source side specs to use single
      # dicts rather than lists of dicts so this can be removed
      dimensions = {}
      for d in dimensions_sequence:
        dimensions.update(d)
    normalized[int(expiration)] = dimensions
  return normalized


def _handle_ci_only(chromium_tests_api, raw_spec, test_spec):
  """Handle the ci_only attribute of test specs.

  Args:
    * chromium_tests_api - The chromium_tests recipe module API object.
    * raw_spec - The source-side spec dictionary describing the test.
    * test_spec - The TestSpec instance for the test.

  Returns:
    The test_spec object that should be used for the test. If the test
    is not ci-only, `test_spec` will be returned unchanged. Otherwise,
    if a CI builder is running, a spec will be returned that includes a
    message indicating that the test will not be run on try builders.
    Otherwise, if the Include-Ci-Only-Test gerrit footer is present and
    evaluates to 'true' when converted to lowercase, a spec will be
    returned that includes a message indicating that the test is being
    run due to the footer. Otherwise, a spec will be returned that
    indicates the test is disabled.
  """
  if not raw_spec.get('ci_only'):
    return test_spec
  if not chromium_tests_api.m.tryserver.is_tryserver:
    return test_spec.add_info_message(
        'This test will not be run on try builders')

  footer_vals = chromium_tests_api.m.tryserver.get_footer(
      steps.INCLUDE_CI_FOOTER)
  disabled = True
  if footer_vals:
    disabled = footer_vals[-1].lower() != 'true'

  if disabled:
    return test_spec.disable(steps.CI_ONLY)
  return test_spec.add_info_message(
      'This test is being run due to the {} gerrit footer'.format(
          steps.INCLUDE_CI_FOOTER))


def generator_common(chromium_tests_api, raw_test_spec, swarming_delegate,
                     local_delegate):
  """Common logic for generating tests from JSON specs.

  Args:
    raw_test_spec: the configuration of the test(s) that should be generated.
    swarming_delegate: function to call to create a swarming test.
    local_delgate: function to call to create a local test.

  Yields:
    instances of Test.
  """

  tests = []
  kwargs = {}

  target_name = raw_test_spec.get('test') or raw_test_spec.get('isolate_name')
  name = raw_test_spec.get('name', target_name)

  kwargs['target_name'] = target_name
  # TODO(crbug.com/1074033): Remove full_test_target.
  kwargs['full_test_target'] = raw_test_spec.get('test_target')
  kwargs['test_id_prefix'] = raw_test_spec.get('test_id_prefix')
  kwargs['name'] = name

  rdb_kwargs = dict(raw_test_spec.get('resultdb', {}))
  rdb_kwargs.setdefault('test_id_prefix', kwargs['test_id_prefix'])
  rdb_kwargs.setdefault(
      'use_rdb_results_for_all_decisions',
      ('chromium.chromium_tests.use_rdb_results' in
       chromium_tests_api.m.buildbucket.build.input.experiments))
  kwargs['resultdb'] = steps.ResultDB.create(**rdb_kwargs)

  processed_set_ups = []
  for s in raw_test_spec.get('setup', []):
    script = s.get('script')
    if script:
      if script.startswith('//'):
        set_up = dict(s)
        set_up['script'] = chromium_tests_api.m.path['checkout'].join(
            script[2:].replace('/', chromium_tests_api.m.path.sep))
        processed_set_ups.append(steps.SetUpScript.create(**set_up))
      else:
        chromium_tests_api.m.python.failing_step(
            'test spec format error',
            textwrap.wrap(
                textwrap.dedent("""\
                    The test target "%s" contains a custom set up script "%s"
                    that doesn't match the expected format. Custom set up script
                    entries should be a path relative to the top-level chromium
                    src directory and should start with "//".
                    """ % (name, script))),
            as_log='details')
  kwargs['set_up'] = processed_set_ups

  processed_tear_downs = []
  for t in raw_test_spec.get('teardown', []):
    script = t.get('script')
    if script:
      if script.startswith('//'):
        tear_down = dict(t)
        tear_down['script'] = chromium_tests_api.m.path['checkout'].join(
            script[2:].replace('/', chromium_tests_api.m.path.sep))
        processed_tear_downs.append(steps.TearDownScript.create(**tear_down))
      else:
        chromium_tests_api.m.python.failing_step(
            'test spec format error',
            textwrap.wrap(
                textwrap.dedent("""\
                    The test target "%s" contains a custom tear down script "%s"
                    that doesn't match the expected format. Custom tear down
                    script entries should be a path relative to the top-level
                    chromium src directory and should start with "//".
                    """ % (name, script))),
            as_log='details')
  kwargs['tear_down'] = processed_tear_downs

  swarming_spec = raw_test_spec.get('swarming', {})
  if swarming_spec.get('can_use_on_swarming_builders'):
    swarming_dimension_sets = swarming_spec.get('dimension_sets')
    swarming_optional_dimensions = _normalize_optional_dimensions(
        swarming_spec.get('optional_dimensions'))
    kwargs['expiration'] = swarming_spec.get('expiration')
    kwargs['containment_type'] = swarming_spec.get('containment_type')
    kwargs['hard_timeout'] = swarming_spec.get('hard_timeout')
    kwargs['io_timeout'] = swarming_spec.get('io_timeout')
    kwargs['shards'] = swarming_spec.get('shards', 1)
    # If idempotent wasn't explicitly set, let chromium_swarming/api.py apply
    # its default_idempotent val.
    if 'idempotent' in swarming_spec:
      kwargs['idempotent'] = swarming_spec['idempotent']

    named_caches = swarming_spec.get('named_caches')
    if named_caches:
      kwargs['named_caches'] = {nc['name']: nc['path'] for nc in named_caches}

    packages = swarming_spec.get('cipd_packages')
    if packages:
      kwargs['cipd_packages'] = [
          chromium_swarming.CipdPackage.create(
              name=p['cipd_package'],
              version=p['revision'],
              root=p['location'],
          ) for p in packages
      ]

    service_account = swarming_spec.get('service_account')
    if service_account:
      kwargs['service_account'] = service_account

    merge = dict(raw_test_spec.get('merge', {}))
    if merge:
      merge_script = merge.get('script')
      if merge_script:
        if merge_script.startswith('//'):
          merge['script'] = chromium_tests_api.m.path['checkout'].join(
              merge_script[2:].replace('/', chromium_tests_api.m.path.sep))
        else:
          chromium_tests_api.m.python.failing_step(
              'test spec format error',
              textwrap.wrap(
                  textwrap.dedent("""\
                      The test target "%s" contains a custom merge_script "%s"
                      that doesn't match the expected format. Custom
                      merge_script entries should be a path relative to the
                      top-level chromium src directory and should start with
                      "//".
                      """ % (name, merge_script))),
              as_log='details')
      kwargs['merge'] = chromium_swarming.MergeScript.create(**merge)

    trigger_script = dict(raw_test_spec.get('trigger_script', {}))
    if trigger_script:
      trigger_script_path = trigger_script.get('script')
      if trigger_script_path:
        if trigger_script_path.startswith('//'):
          trigger_script['script'] = chromium_tests_api.m.path['checkout'].join(
              trigger_script_path[2:].replace('/',
                                              chromium_tests_api.m.path.sep))
        else:
          chromium_tests_api.m.python.failing_step(
              'test spec format error',
              textwrap.wrap(
                  textwrap.dedent("""\
                  The test target "%s" contains a custom trigger_script "%s"
                  that doesn't match the expected format. Custom trigger_script
                  entries should be a path relative to the top-level chromium
                  src directory and should start with "//".
                  """ % (name, trigger_script_path))),
              as_log='details')
      kwargs['trigger_script'] = chromium_swarming.TriggerScript.create(
          **trigger_script)

    for dimensions in swarming_dimension_sets or [{}]:
      kwargs['dimensions'] = dimensions

      # Also, add in optional dimensions.
      kwargs['optional_dimensions'] = swarming_optional_dimensions

      tests.append(swarming_delegate(raw_test_spec, **kwargs))

  else:
    tests.append(local_delegate(raw_test_spec, **kwargs))

  experiment_percentage = raw_test_spec.get('experiment_percentage')
  for t in tests:
    if experiment_percentage is not None:
      yield steps.ExperimentalTestSpec.create(t, experiment_percentage,
                                              chromium_tests_api.m)
    else:
      yield t


def generate_gtests(chromium_tests_api,
                    builder_group,
                    buildername,
                    source_side_spec,
                    bot_update_step,
                    scripts_compile_targets_fn=None):
  del scripts_compile_targets_fn

  def canonicalize_test(test):
    if isinstance(test, basestring):
      canonical_test = {'test': test}
    else:
      canonical_test = dict(test)

    canonical_test.setdefault('shard_index', 0)
    canonical_test.setdefault('total_shards', 1)
    return canonical_test

  def get_tests(api):
    del api
    return [
        canonicalize_test(t)
        for t in source_side_spec.get(buildername, {}).get('gtest_tests', [])
    ]

  for raw_spec in get_tests(chromium_tests_api):
    if raw_spec.get('use_isolated_scripts_api'):
      generator = generate_isolated_script_tests_from_one_spec
    else:
      generator = generate_gtests_from_one_spec

    for test_spec in generator(chromium_tests_api, builder_group, buildername,
                               raw_spec, bot_update_step):
      yield _handle_ci_only(chromium_tests_api, raw_spec, test_spec)


def generate_gtests_from_one_spec(chromium_tests_api, builder_group,
                                  buildername, raw_test_spec, bot_update_step):

  def gtest_delegate_common(raw_test_spec, **kwargs):
    del kwargs
    common_gtest_kwargs = {}
    args = get_args_for_test(chromium_tests_api, raw_test_spec, bot_update_step)
    if raw_test_spec['shard_index'] != 0 or raw_test_spec['total_shards'] != 1:
      args.extend([
          '--test-launcher-shard-index=%d' % raw_test_spec['shard_index'],
          '--test-launcher-total-shards=%d' % raw_test_spec['total_shards']
      ])
    common_gtest_kwargs['args'] = args

    common_gtest_kwargs['override_compile_targets'] = raw_test_spec.get(
        'override_compile_targets', None)

    common_gtest_kwargs['waterfall_builder_group'] = builder_group
    common_gtest_kwargs['waterfall_buildername'] = buildername

    return common_gtest_kwargs

  def gtest_swarming_delegate(raw_test_spec, **kwargs):
    kwargs.update(gtest_delegate_common(raw_test_spec, **kwargs))
    kwargs['isolate_profile_data'] = (
        raw_test_spec.get('isolate_coverage_data') or
        raw_test_spec.get('isolate_profile_data'))
    kwargs['ignore_task_failure'] = raw_test_spec.get('ignore_task_failure',
                                                      False)

    kwargs['resultdb'] = attr.evolve(kwargs['resultdb'], result_format='gtest')
    return steps.SwarmingGTestTestSpec.create(**kwargs)

  def gtest_local_delegate(raw_test_spec, **kwargs):
    kwargs.update(gtest_delegate_common(raw_test_spec, **kwargs))
    kwargs['use_xvfb'] = raw_test_spec.get('use_xvfb', True)

    kwargs['annotate'] = raw_test_spec.get('annotate', 'gtest')
    kwargs['perf_config'] = raw_test_spec.get('perf_config')
    kwargs['perf_builder_name_alias'] = raw_test_spec.get(
        'perf_builder_name_alias')

    kwargs['resultdb'] = attr.evolve(kwargs['resultdb'], result_format='gtest')
    return steps.LocalGTestTestSpec.create(**kwargs)

  for t in generator_common(chromium_tests_api, raw_test_spec,
                            gtest_swarming_delegate, gtest_local_delegate):
    yield t


def generate_junit_tests(chromium_tests_api,
                         builder_group,
                         buildername,
                         source_side_spec,
                         bot_update_step,
                         scripts_compile_targets_fn=None):
  del bot_update_step, scripts_compile_targets_fn

  for raw_spec in source_side_spec.get(buildername, {}).get('junit_tests', []):
    rdb_kwargs = dict(raw_spec.get('resultdb', {}))
    rdb_kwargs.setdefault('test_id_prefix', raw_spec.get('test_id_prefix'))
    rdb_kwargs.setdefault(
        'use_rdb_results_for_all_decisions',
        ('chromium.chromium_tests.use_rdb_results' in
         chromium_tests_api.m.buildbucket.build.input.experiments))
    resultdb = steps.ResultDB.create(**rdb_kwargs)

    test_spec = steps.AndroidJunitTestSpec.create(
        raw_spec.get('name', raw_spec['test']),
        target_name=raw_spec['test'],
        additional_args=raw_spec.get('args'),
        waterfall_builder_group=builder_group,
        waterfall_buildername=buildername,
        resultdb=resultdb)
    yield _handle_ci_only(chromium_tests_api, raw_spec, test_spec)


def generate_script_tests(chromium_tests_api,
                          builder_group,
                          buildername,
                          source_side_spec,
                          bot_update_step,
                          scripts_compile_targets_fn=None):
  # Unused arguments
  del bot_update_step

  for raw_spec in source_side_spec.get(buildername, {}).get('scripts', []):
    rdb_kwargs = dict(raw_spec.get('resultdb', {'enable': True}))
    rdb_kwargs.setdefault('test_id_prefix', raw_spec.get('test_id_prefix'))
    rdb_kwargs.setdefault(
        'use_rdb_results_for_all_decisions',
        ('chromium.chromium_tests.use_rdb_results' in
         chromium_tests_api.m.buildbucket.build.input.experiments))
    resultdb = steps.ResultDB.create(**rdb_kwargs)

    test_spec = steps.ScriptTestSpec.create(
        str(raw_spec['name']),
        script=raw_spec['script'],
        all_compile_targets=scripts_compile_targets_fn(),
        script_args=raw_spec.get('args', []),
        override_compile_targets=raw_spec.get('override_compile_targets', []),
        waterfall_builder_group=builder_group,
        waterfall_buildername=buildername,
        resultdb=resultdb)
    yield _handle_ci_only(chromium_tests_api, raw_spec, test_spec)


def generate_isolated_script_tests(chromium_tests_api,
                                   builder_group,
                                   buildername,
                                   source_side_spec,
                                   bot_update_step,
                                   scripts_compile_targets_fn=None):
  del scripts_compile_targets_fn

  for raw_spec in source_side_spec.get(buildername,
                                       {}).get('isolated_scripts', []):
    for test_spec in generate_isolated_script_tests_from_one_spec(
        chromium_tests_api, builder_group, buildername, raw_spec,
        bot_update_step):
      yield _handle_ci_only(chromium_tests_api, raw_spec, test_spec)


def generate_isolated_script_tests_from_one_spec(chromium_tests_api,
                                                 builder_group, buildername,
                                                 raw_test_spec,
                                                 bot_update_step):

  def isolated_script_delegate_common(test, name=None, **kwargs):
    del kwargs

    common_kwargs = {}

    # The variable substitution and precommit/non-precommit arguments
    # could be supported for the other test types too, but that wasn't
    # desired at the time of this writing.
    common_kwargs['args'] = get_args_for_test(chromium_tests_api, test,
                                              bot_update_step)
    # This features is only needed for the cases in which the *_run compile
    # target is needed to generate isolate files that contains dynamically libs.
    # TODO(nednguyen, kbr): Remove this once all the GYP builds are converted
    # to GN.
    common_kwargs['override_compile_targets'] = test.get(
        'override_compile_targets', None)
    common_kwargs['isolate_profile_data'] = (
        test.get('isolate_coverage_data') or test.get('isolate_profile_data'))

    # TODO(tansell): Remove this once custom handling of results is no longer
    # needed.
    results_handler_name = test.get('results_handler', 'default')
    if results_handler_name not in steps.ALLOWED_RESULT_HANDLER_NAMES:
      chromium_tests_api.m.python.failing_step(
          'isolated_scripts spec format error',
          textwrap.wrap(
              textwrap.dedent("""\
                  The isolated_scripts target "%s" contains a custom
                  results_handler "%s" but that result handler was not found.
                  """ % (name, results_handler_name))),
          as_log='details')
    common_kwargs['results_handler_name'] = results_handler_name

    return common_kwargs

  def isolated_script_swarming_delegate(raw_test_spec, **kwargs):
    kwargs.update(isolated_script_delegate_common(raw_test_spec, **kwargs))

    swarming_spec = raw_test_spec.get('swarming', {})

    kwargs['ignore_task_failure'] = swarming_spec.get('ignore_task_failure',
                                                      False)
    kwargs['waterfall_buildername'] = buildername
    kwargs['waterfall_builder_group'] = builder_group

    resultdb = kwargs['resultdb']
    # HACK: If an isolated script test doesn't explicitly enable resultdb in
    # its test spec, assume it doesn't have native integration with result-sink
    # and consequently needs the result_adapter added using the 'json' format.
    # TODO(crbug.com/1135718): Explicitly mark all such tests as using the
    # json result format in the testing specs.
    rdb_kwargs = dict(raw_test_spec.get('resultdb', {}))
    if not rdb_kwargs:
      resultdb = attr.evolve(resultdb, result_format='json')
    kwargs['resultdb'] = resultdb

    return steps.SwarmingIsolatedScriptTestSpec.create(**kwargs)

  def isolated_script_local_delegate(raw_test_spec, **kwargs):
    kwargs.update(isolated_script_delegate_common(raw_test_spec, **kwargs))
    return steps.LocalIsolatedScriptTestSpec.create(**kwargs)

  for t in generator_common(chromium_tests_api, raw_test_spec,
                            isolated_script_swarming_delegate,
                            isolated_script_local_delegate):
    yield t


def generate_skylab_tests(chromium_tests_api,
                          builder_group,
                          buildername,
                          source_side_spec,
                          bot_update_step,
                          swarming_dimensions=None,
                          scripts_compile_targets_fn=None):
  del scripts_compile_targets_fn, swarming_dimensions

  def generate_skylab_tests_from_one_spec(builder_group, buildername,
                                          skylab_test_spec):
    kwargs_to_forward = set(
        k for k in attr.fields_dict(steps.SkylabTestSpec)
        if not k in ['test_args', 'resultdb'])
    common_skylab_kwargs = {
        k: v for k, v in skylab_test_spec.items() if k in kwargs_to_forward
    }
    rdb_kwargs = dict(skylab_test_spec.pop('resultdb', {}))
    common_skylab_kwargs['resultdb'] = steps.ResultDB.create(**rdb_kwargs)
    common_skylab_kwargs['test_args'] = get_args_for_test(
        chromium_tests_api, skylab_test_spec, bot_update_step)
    common_skylab_kwargs['target_name'] = skylab_test_spec.get('test')
    common_skylab_kwargs['waterfall_builder_group'] = builder_group
    common_skylab_kwargs['waterfall_buildername'] = buildername
    return steps.SkylabTestSpec.create(
        skylab_test_spec.get('name'), **common_skylab_kwargs)

  for raw_spec in source_side_spec.get(buildername, {}).get('skylab_tests', []):
    test_spec = generate_skylab_tests_from_one_spec(builder_group, buildername,
                                                    raw_spec)
    yield _handle_ci_only(chromium_tests_api, raw_spec, test_spec)


ALL_GENERATORS = [
    generate_isolated_script_tests,
    generate_gtests,
    generate_junit_tests,
    generate_script_tests,
    generate_skylab_tests,
]
