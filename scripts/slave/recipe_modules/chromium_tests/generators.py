# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import string
import textwrap

from . import steps


def get_args_for_test(api, chromium_tests_api, test_spec, bot_update_step):
  """Gets the argument list for a dynamically generated test, as
  provided by the JSON files in src/testing/buildbot/ in the Chromium
  workspace. This function provides the following build properties in
  the form of variable substitutions in the tests' argument lists:

      buildbucket_build_id
      buildername
      buildnumber
      got_revision
      mastername
      patch_issue
      patch_set

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
  """

  args = test_spec.get('args', [])
  extra_args = None
  if chromium_tests_api.is_precommit_mode():
    extra_args = test_spec.get('precommit_args', [])
  else:
    extra_args = test_spec.get('non_precommit_args', [])
  # Only add the extra args if there were any to prevent cases of mixed
  # tuple/list concatenation caused by assuming type
  if extra_args:
    args = args + extra_args

  # Perform substitution of known variables.
  build = chromium_tests_api.m.buildbucket.build
  cl = (build.input.gerrit_changes or [None])[0]
  substitutions = {
      'buildbucket_build_id': build.id,
      'buildername': build.builder.builder,
      'buildnumber': build.number,
      'got_revision': (
          bot_update_step.presentation.properties.get('got_revision',
          bot_update_step.presentation.properties.get('got_src_revision'))),
      'mastername': api.properties.get('mastername'),
      'patch_issue': cl.change if cl else None,
      'patch_set': cl.patchset if cl else None,
  }
  return [string.Template(arg).safe_substitute(substitutions) for arg in args]


def generator_common(api, spec, swarming_delegate, local_delegate,
                     swarming_dimensions):
  """Common logic for generating tests from JSON specs.

  Args:
    spec: the configuration of the test(s) that should be generated.
    swarming_delegate: function to call to create a swarming test.
    local_delgate: function to call to create a local test.

  Yields:
    instances of Test.
  """

  tests = []
  kwargs = {}

  target_name = spec.get('test') or spec.get('isolate_name')
  name = spec.get('name', target_name)

  kwargs['target_name'] = target_name
  kwargs['name'] = name

  set_up = list(spec.get('setup', []))
  processed_set_up = []
  for set_up_step in set_up:
    set_up_step_script = set_up_step.get('script')
    if set_up_step_script:
      if set_up_step_script.startswith('//'):
        set_up_step_new = dict(set_up_step)
        set_up_step_new['script'] = api.path['checkout'].join(
            set_up_step_script[2:].replace('/', api.path.sep))
        processed_set_up.append(set_up_step_new)
      else:
        api.python.failing_step(
          'test spec format error',
          textwrap.wrap(textwrap.dedent("""\
              The test target "%s" contains a custom set up script "%s"
              that doesn't match the expected format. Custom set up script entries
              should be a path relative to the top-level chromium src directory and
              should start with "//".
              """ % (name, set_up_step_script))),
          as_log='details')
  kwargs['set_up'] = processed_set_up

  tear_down = list(spec.get('teardown', []))
  processed_tear_down = []
  for tear_down_step in tear_down:
    tear_down_step_script = tear_down_step.get('script')
    if tear_down_step_script:
      if tear_down_step_script.startswith('//'):
        tear_down_step_new = dict(tear_down_step)
        tear_down_step_new['script'] = api.path['checkout'].join(
            tear_down_step_script[2:].replace('/', api.path.sep))
        processed_tear_down.append(tear_down_step_new)
      else:
        api.python.failing_step(
          'test spec format error',
          textwrap.wrap(textwrap.dedent("""\
              The test target "%s" contains a custom tear down script "%s"
              that doesn't match the expected format. Custom tear down script entries
              should be a path relative to the top-level chromium src directory and
              should start with "//".
              """ % (name, tear_down_step_script))),
          as_log='details')
  kwargs['tear_down'] = processed_tear_down

  swarming_spec = spec.get('swarming', {})
  if swarming_spec.get('can_use_on_swarming_builders'):
    swarming_dimension_sets = swarming_spec.get('dimension_sets')
    swarming_optional_dimensions = swarming_spec.get(
        'optional_dimensions')
    kwargs['expiration'] = swarming_spec.get('expiration')
    kwargs['hard_timeout'] = swarming_spec.get('hard_timeout')
    kwargs['io_timeout'] = swarming_spec.get('io_timeout')
    kwargs['shards'] = swarming_spec.get('shards', 1)

    packages = swarming_spec.get('cipd_packages')
    if packages:
      kwargs['cipd_packages'] = [
          (p['location'], p['cipd_package'], p['revision'])
          for p in packages
      ]

    service_account = swarming_spec.get('service_account')
    if service_account:
      kwargs['service_account'] = service_account

    merge = dict(spec.get('merge', {}))
    if merge:
      merge_script = merge.get('script')
      if merge_script:
        if merge_script.startswith('//'):
          merge['script'] = api.path['checkout'].join(
              merge_script[2:].replace('/', api.path.sep))
        else:
          api.python.failing_step(
              'test spec format error',
              textwrap.wrap(textwrap.dedent("""\
                  The test target "%s" contains a custom merge_script "%s"
                  that doesn't match the expected format. Custom merge_script entries
                  should be a path relative to the top-level chromium src directory and
                  should start with "//".
                  """ % (name, merge_script))),
              as_log='details')
    kwargs['merge'] = merge

    trigger_script = dict(spec.get('trigger_script', {}))
    if trigger_script:
      trigger_script_path = trigger_script.get('script')
      if trigger_script_path:
        if trigger_script_path.startswith('//'):
          trigger_script['script'] = api.path['checkout'].join(
              trigger_script_path[2:].replace('/', api.path.sep))
        else:
          api.python.failing_step(
              'test spec format error',
              textwrap.wrap(textwrap.dedent("""\
                  The test target "%s" contains a custom trigger_script "%s"
                  that doesn't match the expected format. Custom trigger_script entries
                  should be a path relative to the top-level chromium src directory and
                  should start with "//".
                  """ % (name, trigger_script_path))),
              as_log='details')
    kwargs['trigger_script'] = trigger_script

    swarming_dimensions = swarming_dimensions or {}
    for dimensions in swarming_dimension_sets or [{}]:
      # Yield potentially multiple invocations of the same test, on
      # different machine configurations.
      new_dimensions = dict(swarming_dimensions)
      new_dimensions.update(dimensions)
      kwargs['dimensions'] = new_dimensions

      # Also, add in optional dimensions.
      kwargs['optional_dimensions'] = swarming_optional_dimensions

      tests.append(swarming_delegate(spec, **kwargs))

  else:
    tests.append(local_delegate(spec, **kwargs))

  experiment_percentage = spec.get('experiment_percentage')
  for t in tests:
    if experiment_percentage is not None:
      yield steps.ExperimentalTest(t, experiment_percentage, api)
    else:
      yield t


def generate_gtest(api, chromium_tests_api, mastername, buildername, test_spec,
                   bot_update_step,
                   swarming_dimensions=None, scripts_compile_targets=None,
                   bot_config=None):
  del scripts_compile_targets, bot_config

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
    return [canonicalize_test(t) for t in
            test_spec.get(buildername, {}).get('gtest_tests', [])]

  def gtest_delegate_common(spec, **kwargs):
    del kwargs
    common_gtest_kwargs = {}
    args = get_args_for_test(api, chromium_tests_api, spec, bot_update_step)
    if spec['shard_index'] != 0 or spec['total_shards'] != 1:
      args.extend(['--test-launcher-shard-index=%d' % spec['shard_index'],
                   '--test-launcher-total-shards=%d' % spec['total_shards']])
    common_gtest_kwargs['args'] = args

    common_gtest_kwargs['override_compile_targets'] = spec.get(
        'override_compile_targets', None)

    common_gtest_kwargs['waterfall_mastername'] = mastername
    common_gtest_kwargs['waterfall_buildername'] = buildername

    return common_gtest_kwargs

  def gtest_swarming_delegate(spec, **kwargs):
    kwargs.update(gtest_delegate_common(spec, **kwargs))
    kwargs['isolate_coverage_data'] = spec.get('isolate_coverage_data')
    return steps.SwarmingGTestTest(**kwargs)

  def gtest_local_delegate(spec, **kwargs):
    kwargs.update(gtest_delegate_common(spec, **kwargs))
    kwargs['use_xvfb'] = spec.get('use_xvfb', True)
    return steps.LocalGTestTest(**kwargs)

  for spec in get_tests(api):
    for t in generator_common(
        api, spec, gtest_swarming_delegate, gtest_local_delegate,
        swarming_dimensions):
      yield t


def generate_junit_test(api, chromium_tests_api, mastername, buildername,
                        test_spec, bot_update_step,
                        swarming_dimensions=None,
                        scripts_compile_targets=None,
                        bot_config=None):
  del api, chromium_tests_api, bot_update_step
  del swarming_dimensions, scripts_compile_targets, bot_config
  for test in test_spec.get(buildername, {}).get('junit_tests', []):
    yield steps.AndroidJunitTest(
        str(test['test']),
        waterfall_mastername=mastername, waterfall_buildername=buildername)


def generate_cts_test(api, chromium_tests_api, mastername, buildername,
                      test_spec, bot_update_step,
                      swarming_dimensions=None,
                      scripts_compile_targets=None,
                      bot_config=None):
  # Unused arguments
  del api, chromium_tests_api, bot_update_step, swarming_dimensions
  del scripts_compile_targets, bot_config

  for test in test_spec.get(buildername, {}).get('cts_tests', []):
    yield steps.WebViewCTSTest(
        platform=str(test['platform']),
        command_line_args=test.get('command_line_args'),
        arch=test.get('arch', 'arm64'),
        waterfall_mastername=mastername, waterfall_buildername=buildername)


def generate_script(api, chromium_tests_api, mastername, buildername, test_spec,
                    bot_update_step,
                    swarming_dimensions=None, scripts_compile_targets=None,
                    bot_config=None):
  # Unused arguments
  del api, chromium_tests_api, bot_update_step, swarming_dimensions
  del bot_config

  for script_spec in test_spec.get(buildername, {}).get('scripts', []):
    yield steps.ScriptTest(
        str(script_spec['name']),
        script_spec['script'],
        scripts_compile_targets,
        script_spec.get('args', []),
        script_spec.get('override_compile_targets', []),
        waterfall_mastername=mastername, waterfall_buildername=buildername)


def generate_isolated_script(api, chromium_tests_api, mastername, buildername,
                             test_spec, bot_update_step,
                             swarming_dimensions=None,
                             scripts_compile_targets=None):
  del scripts_compile_targets
  def isolated_script_delegate_common(test, name=None, **kwargs):
    del kwargs

    common_kwargs = {}

    # The variable substitution and precommit/non-precommit arguments
    # could be supported for the other test types too, but that wasn't
    # desired at the time of this writing.
    common_kwargs['args'] = get_args_for_test(
        api, chromium_tests_api, test, bot_update_step)
    # This features is only needed for the cases in which the *_run compile
    # target is needed to generate isolate files that contains dynamically libs.
    # TODO(nednguyen, kbr): Remove this once all the GYP builds are converted
    # to GN.
    common_kwargs['override_compile_targets'] = test.get(
        'override_compile_targets', None)
    common_kwargs['isolate_coverage_data'] = test.get('isolate_coverage_data')

    # TODO(tansell): Remove this once custom handling of results is no longer
    # needed.
    results_handler_name = test.get('results_handler', 'default')
    try:
        common_kwargs['results_handler'] = {
            'default': lambda: None,
            'fake': steps.FakeCustomResultsHandler,
            'layout tests': steps.LayoutTestResultsHandler,
        }[results_handler_name]()
    except KeyError:
      api.python.failing_step(
          'isolated_scripts spec format error',
          textwrap.wrap(textwrap.dedent("""\
              The isolated_scripts target "%s" contains a custom results_handler
              "%s" but that result handler was not found.
              """ % (name, results_handler_name))),
          as_log='details')

    return common_kwargs

  def isolated_script_swarming_delegate(spec, **kwargs):
    kwargs.update(isolated_script_delegate_common(spec, **kwargs))

    swarming_spec = spec.get('swarming', {})

    kwargs['ignore_task_failure'] = swarming_spec.get(
        'ignore_task_failure', False)
    kwargs['waterfall_buildername'] = buildername
    kwargs['waterfall_mastername'] = mastername
    kwargs['idempotent'] = swarming_spec.get('idempotent', True)

    return steps.SwarmingIsolatedScriptTest(**kwargs)

  def isolated_script_local_delegate(spec, **kwargs):
    kwargs.update(isolated_script_delegate_common(spec, **kwargs))
    return steps.LocalIsolatedScriptTest(**kwargs)

  for spec in test_spec.get(buildername, {}).get('isolated_scripts', []):
    for t in generator_common(
        api, spec, isolated_script_swarming_delegate,
        isolated_script_local_delegate, swarming_dimensions):
      yield t

