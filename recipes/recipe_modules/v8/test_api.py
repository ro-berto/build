# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

import argparse
import ast
from collections import OrderedDict
import re

from recipe_engine import recipe_test_api
from recipe_engine.post_process import DoesNotRun, Filter, MustRun
from . import builders
from . import testing

from PB.go.chromium.org.luci.scheduler.api.scheduler.v1 import (
    triggers as triggers_pb2)

# Excerpt of the v8 version file.
VERSION_FILE_TMPL = """
#define V8_MAJOR_VERSION 3
#define V8_MINOR_VERSION 4
#define V8_BUILD_NUMBER 3
#define V8_PATCH_LEVEL %d
"""


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


class V8TestApi(recipe_test_api.RecipeTestApi):
  @staticmethod
  def SLOWEST_TESTS():
    return [
        {
            'name': 'mjsunit/Cool.Test',
            'flags': ['-f'],
            'command': 'd8 -f mjsunit/Cool.Test',
            'duration': 61.0028,
        },
        {
            'name': 'mjsunit/Cool.Test2',
            'flags': ['-f', '-g'],
            'command': 'd8 -f mjsunit/Cool.Test2',
            'duration': 0.1012,
        },
    ]

  def output_json(self, has_failures=False, flakes=False,
                  unmarked_slow_test=False):
    slowest_tests = V8TestApi.SLOWEST_TESTS()
    # The collect step is still on legacy @@@annotation@@@
    successful_collect_step = self.m.legacy_annotation.success_step
    if unmarked_slow_test:
      slowest_tests += [{
        'name': 'mjsunit/slow',
        'flags': [],
        'command': 'd8 -f mjsunit/slow',
        'duration': 123.0,
        'marked_slow': False,
      }]
    if not has_failures:
      return successful_collect_step + self.m.json.output({
        'results': [],
        'slowest_tests': slowest_tests,
        'tags': [],
      })
    if flakes:
      return successful_collect_step + self.m.json.output({
        'results': [
          {
            'flags': [],
            'result': 'FAIL',
            'expected': ['PASS', 'SLOW'],
            'duration': 3,
            'variant': 'default',
            'random_seed': 123,
            'run': 1,
            'stdout': 'Some output.',
            'stderr': 'Some errput.',
            'name': 'suite-name/dir/test-name',
            'command': 'd8 test.js',
            'exit_code': 1,
          },
          {
            'flags': [],
            'result': 'PASS',
            'expected': ['PASS', 'SLOW'],
            'duration': 10,
            'variant': 'default',
            'random_seed': 123,
            'run': 2,
            'stdout': 'Some output.',
            'stderr': '',
            'name': 'suite-name/dir/test-name',
            'command': 'd8 test.js',
            'exit_code': 1,
          },
          {
            'flags': [],
            'result': 'FAIL',
            'expected': ['PASS', 'SLOW'],
            'duration': 1.5,
            'variant': 'default',
            'random_seed': 123,
            'run': 1,
            'stdout': 'Some output.',
            'stderr': 'Some errput.',
            'name': 'suite-name/dir/test-name2',
            'command': 'd8 test.js',
            'exit_code': 1,
          },
          {
            'flags': [],
            'result': 'PASS',
            'expected': ['PASS', 'SLOW'],
            'duration': 10,
            'variant': 'default',
            'random_seed': 123,
            'run': 2,
            'stdout': 'Some output.',
            'stderr': '',
            'name': 'suite-name/dir/test-name2',
            'command': 'd8 test.js',
            'exit_code': 1,
          },
        ],
        'slowest_tests': slowest_tests,
        'tags': [],
      })


    # Add enough failures to exceed the maximum number of shown failures
    # (test-name9 will be cut off).
    results = []
    for i in range(0, 10):
      results.append({
        'flags': ['--opt42'],
        'result': 'FAIL',
        'expected': ['PASS', 'SLOW'],
        'duration': 61.0028,
        'variant': 'default',
        'random_seed': 123,
        'run': 1,
        'stdout': 'Some output.',
        'stderr': 'Some errput.',
        'name': 'suite-name/dir/test-name%d' % i,
        'command': 'out/theMode/d8 --opt42 test/suite-name/dir/test-name.js',
        'exit_code': 1,
      })
      results.append({
        'flags': ['--other'],
        'result': 'FAIL',
        'duration': 3599.9999,
        'variant': 'default',
        'random_seed': 123,
        'run': 1,
        'stdout': 'Some output.',
        'stderr': 'Some errput.',
        'name': 'suite-name/dir/test-name%d' % i,
        'command': 'out/theMode/d8 --other test/suite-name/dir/test-name.js',
        'exit_code': 1,
      })
      results.append({
        'flags': ['--other'],
        'result': 'CRASH',
        'duration': 0.1111,
        'variant': 'default',
        'random_seed': 123,
        'run': 1,
        'stdout': 'Some output\nwith\nmore\nlines.',
        'stderr': 'Some errput.',
        'name': 'other-suite/dir/other-test-very-very-very-long-name%d' % i,
        'command': (
          'out/theMode/d8 --other test/other-suite/dir/other-test-very-very-'
          'very-long-name.js'),
        'exit_code': 1,
      })

    return successful_collect_step + self.m.json.output({
      'results': results,
      'slowest_tests': slowest_tests,
      'tags': [],
    })

  def one_failure(self):
    return self.m.json.output({
      'results': [
        {
          'flags': [],
          'result': 'FAIL',
          'expected': ['PASS', 'SLOW'],
          'duration': 5,
          'variant': 'default',
          'random_seed': 123,
          'run': 1,
          'stdout': 'Some output.',
          'stderr': 'Some errput.',
          'name': 'suite-name/dir/test-name',
          'command': 'd8 test.js',
          'target_name': 'd8',
          'exit_code': 1,
        },
      ],
      'slowest_tests': V8TestApi.SLOWEST_TESTS(),
      'tags': [],
    }) + self.m.legacy_annotation.success_step

  def one_flake(self, num_fuzz=False):
    if num_fuzz:
      framework_name = 'num_fuzzer'
      variant = None
      variant_flags = ['--flag1', '--flag2']
    else:
      framework_name = 'standard_runner'
      variant = 'stress'
      variant_flags = None

    return self.m.json.output({
      'results': [
        {
          'flags': [],
          'result': 'FAIL',
          'expected': ['PASS', 'SLOW'],
          'duration': 3,
          'variant': variant,
          'variant_flags': variant_flags,
          'random_seed': 123,
          'run': 1,
          'stdout': 'Some output.',
          'stderr': 'Some errput.',
          'name': 'suite-name/dir/test-name',
          'command': 'd8 test.js',
          'exit_code': 1,
          'framework_name': framework_name,
        },
        {
          'flags': [],
          'result': 'PASS',
          'expected': ['PASS', 'SLOW'],
          'duration': 10,
          'variant': variant,
          'variant_flags': variant_flags,
          'random_seed': 123,
          'run': 2,
          'stdout': 'Some output.',
          'stderr': '',
          'name': 'suite-name/dir/test-name',
          'command': 'd8 test.js',
          'exit_code': 0,
          'framework_name': framework_name,
        },
      ],
      'slowest_tests': V8TestApi.SLOWEST_TESTS(),
      'tags': [],
    }) + self.m.legacy_annotation.success_step

  def infra_failure(self):
    return self.m.json.output({
      'results': [],
      'slowest_tests': V8TestApi.SLOWEST_TESTS(),
      'tags': ['UNRELIABLE_RESULTS'],
    }) + self.m.legacy_annotation.success_step

  def failures_example(self, variant1='default', variant2='default'):
    flags = {'default': '', 'stress': ' --stress-opt'}
    return self.m.json.output({
      'results': [
        {
          'flags': [],
          'result': 'FAIL',
          'expected': ['PASS', 'SLOW'],
          'duration': 3,
          'variant': variant1,
          'random_seed': 123,
          'run': 1,
          'stdout': 'Some output.',
          'stderr': 'Some errput.',
          'name': 'suite-name/dir/slow',
          'command': 'd8%s test.js' % flags[variant1],
          'target_name': 'd8',
          'exit_code': 1,
        },
        {
          'flags': [],
          'result': 'FAIL',
          'expected': ['PASS', 'SLOW'],
          'duration': 1.5,
          'variant': variant2,
          'random_seed': 123,
          'run': 1,
          'stdout': 'Some output.',
          'stderr': 'Some errput.',
          'name': 'suite-name/dir/fast',
          'command': 'd8%s test.js' % flags[variant2],
          'target_name': 'd8',
          'exit_code': 1,
        },
      ],
      'slowest_tests': V8TestApi.SLOWEST_TESTS(),
      'tags': [],
    }) + self.m.legacy_annotation.success_step

  def example_scheduler_buildbucket_trigger(self, key='a'):
    trigger = triggers_pb2.Trigger(id=key)
    trigger.buildbucket.properties['oldest_gitiles_revision'] = 40*key
    trigger.buildbucket.properties['newest_gitiles_revision'] = 40*key
    return trigger

  def example_scheduler_gitiles_trigger(self, key='a'):
    return triggers_pb2.Trigger(
        id=key,
        gitiles=dict(
            repo='https://chromium.googlesource.com/v8/v8',
            ref='refs/heads/main',
            revision=key * 40,
        ))

  def example_bisection_range(self):
    # Gitiles returns changes in the order child -> parent.
    return self.m.json.output({
      'log': [
        {'commit': 'a3', 'msg': 'Cool commit 3'},
        {'commit': 'a2', 'msg': 'Cool commit 2'},
        {'commit': 'a1', 'msg': 'Cool commit 1'},
        {'commit': 'a0', 'msg': 'Cool commit 0'},
      ],
    })

  def example_bisection_range_one_change(self):
    # A1 is the single change in the range, while a0 is the latest previous
    # before the range.
    return self.m.json.output({
      'log': [
        {'commit': 'a1', 'msg': 'Cool commit 1'},
        {'commit': 'a0', 'msg': 'Cool commit 0'},
      ],
    })

  def example_available_builds(self, revision):
    # When 'gsutil ls' is called, it will only find builds for a1 or a3.
    available_builds = {
      'a1': 'gs://chromium-v8/v8-linux64-dbg/full-build-linux_a1.zip',
      'a3': 'gs://chromium-v8/v8-linux64-dbg/full-build-linux_a3.zip',
    }
    return self.m.raw_io.stream_output_text(
        available_builds.get(revision, ''),
        stream='stdout',
    )

  def example_build_dependencies(self):
    return self.m.json.output({
      'avg_deps': 1.2,
      'by_extension': {
        'h': {
          'avg_deps': 53.7,
          'num_files': 53,
          'top100_avg_deps': 67.2,
          'top200_avg_deps': 55.1,
          'top500_avg_deps': 34.94,
        }
      },
      'num_files': 3615,
      'top100_avg_deps': 1.3,
    })

  def example_test_roots(self, *roots):
    """Simulates dynamically optained test-root directories."""
    return self.override_step_data(
        'initialization.list test roots',
        self.m.file.listdir(roots),
    )

  def example_test_config(self, test_config):
    """Simulates reading a simple test-config file.

    Args:
      test_config: The raw test config pyl text.
    """
    return self.m.file.read_text(test_config)

  def example_test_spec(self, builder, spec):
    """Simulates reading a simple test-spec file with one builder.

    Args:
      builder: Key the spec by this builder.
      spec: The raw test spec pyl text.
    """
    return self.m.file.read_text('{"%s": %s}' % (builder, spec))

  def example_parent_test_spec_properties(self, buildername, spec):
    """Properties dict containing an example parent_test_spec.

    Args:
      buildername: Name of the builder that should get this property.
      spec: The raw test spec pyl text.
    Returns: A dict with a parent_test_spec key set to a packed test spec.
    """
    return builders.TestSpec.from_python_literal(
        {buildername: ast.literal_eval(spec)},
        [buildername],
    ).as_properties_dict(buildername)

  def example_build_config(self):
    """Fake config file with build information as written by V8's BUILD.gn."""
    return self.m.json.output({
      "dcheck_always_on": False,
      "is_debug": False,
      "target_cpu": "x64",
      "v8_target_cpu": "x64",
    })

  def test_spec_in_checkout(self, buildername, test_spec, testername=None):
    """Simulates having a test specification in the checkout (i.e. on a
    builder_tester bot).

    If testername is specified, we simulate data for a pure compiler builder
    that's supposed to trigger a tester.
    """
    return (
        self.m.path.exists(self.m.path['cache'].join(
            'builder', 'v8', 'infra', 'testing', 'builders.pyl')) +
        self.step_data(
            'initialization.read test spec (v8)',
            self.example_test_spec(testername or buildername, test_spec),
        )
    )

  def hide_infra_steps(self):
    """This hides some infra steps in the expectations which are tested
    sufficiently elsewhere.
    """
    skip_fragments = map(re.escape, [
      'ensure builder cache dir',
      'ensure_goma',
      'preprocess_for_goma',
      'postprocess_for_goma',
      'read revision',
    ])
    return self.post_process(
        Filter().include_re(r'^((?!(.*\.)?%s).)*$' % '|'.join(skip_fragments)))

  def version_file(self, patch_level, desc, count=1, prefix=''):
    # Recipe step name disambiguation.
    suffix = ' (%d)' % count if count > 1 else ''
    return self.override_step_data(
        '%sCheck %s version file%s' % (prefix, desc, suffix),
        self.m.raw_io.stream_output_text(
            VERSION_FILE_TMPL % patch_level,
            stream='stdout'),
    )

  def _make_dummy_swarm_hashes(self, test_names):
    """Makes dummy isolate hashes for all tests of a bot.

    Either an explicit isolate target must be defined or the naming
    convention "test name == isolate target name" will be used.
    """
    def gen_isolate_targets(test_name):
      config = testing.TEST_CONFIGS.get(test_name, {})
      if config.get('isolated_target'):
        yield config['isolated_target']
      else:
        for test in config.get('tests', []):
          yield test

    return dict(
        (target, '[dummy hash for %s]/123' % target)
        for test_name in test_names
        for target in gen_isolate_targets(test_name)
    )

  def test_name(self, builder_group, buildername, suffix=''):
    return '_'.join(
        filter(bool, [
            'full',
            _sanitize_nonalpha(builder_group),
            _sanitize_nonalpha(buildername),
            suffix,
        ]))

  def test(self,
           builder_group,
           buildername,
           suffix='',
           parent_test_spec=None,
           parent_buildername=None,
           parent_bot_config=None,
           git_ref='refs/heads/main',
           experiments=None,
           **kwargs):
    """Convenience method to generate test data for V8 recipe runs.

    Args:
      builder_group: The group of the builder to run.
      buildername: Buildername property as passed to the recipe.
      suffix: Test name suffix.
      parent_test_spec: Test-spec property passed to testers.
      parent_buildername: Name of the parent builder when simulating a child
          tester. Default value if no static config exists in builders.py.
      parent_bot_config: Content of the parent's bot_config when simulating a
          child tester. Default value if no static config exists in builders.py.
      git_ref: Ref from which a commit is fetched.

    """
    if parent_test_spec:
      kwargs.update(self.example_parent_test_spec_properties(
          buildername, parent_test_spec))

    if 'triggers' in kwargs:
      # Freezing the structure in builders.py turns lists into tuples. But
      # the recipe properties api requires type list for triggers just like in
      # prod.
      kwargs['triggers'] = list(kwargs['triggers'])

    if builder_group.startswith('tryserver'):
      properties_fn = self.m.properties.tryserver
    else:
      properties_fn = self.m.properties.generic

    test = recipe_test_api.RecipeTestApi.test(
        self.test_name(builder_group, buildername, suffix),
        properties_fn(
            parent_buildername=parent_buildername,
            gerrit_project='v8/v8',
            # TODO(sergiyb): Remove this property after archive module has been
            # migrated to new buildbucket properties.
            buildername=buildername,
            **kwargs),
        self.m.builder_group.for_current(builder_group),
        self.m.platform('linux', 64),
    )
    if parent_buildername:
      test += self.m.properties(
          parent_got_revision='deafbeef'*5,
          parent_got_revision_cp='refs/heads/master@{#20123}',
          parent_gn_args=[
            'use_goma = true', 'also_interesting = "absolutely"'],
          parent_build='https://someinfrasite.com/build/123',
      )
      test += self.m.scheduler(triggers=[
        self.example_scheduler_buildbucket_trigger('a'),
        self.example_scheduler_buildbucket_trigger('b'),
      ])
      if kwargs.get('enable_swarming', True):
        # Assume each tester is triggered with the required hashes for all
        # tests. Assume extra_isolate hashes for each extra test specified by
        # parent_test_spec property.
        buider_spec = kwargs.get('parent_test_spec', {})
        swarm_hashes = self._make_dummy_swarm_hashes(
            test[0] for test in buider_spec.get('tests', []))
        test += self.m.properties(
          parent_got_swarming_client_revision='[dummy swarming client hash]',
          swarm_hashes=swarm_hashes,
        )
    else:  # triggering builder
      test += self.m.scheduler(triggers=[
        self.example_scheduler_gitiles_trigger('a'),
        self.example_scheduler_gitiles_trigger('b'),
      ])

    if builder_group.startswith('tryserver'):
      test += self.m.properties(
          category='cq',
          master='tryserver.v8',
          reason='CQ',
          try_job_key='1234',
      ) + self.m.buildbucket.try_build(
          project='v8',
          revision='deadbeef'*5,
          builder=buildername,
          git_repo='https://chromium.googlesource.com/v8/v8',
          change_number=456789,
          patch_set=12,
          tags=self.m.buildbucket.tags(
              user_agent='cq',
              buildset='patch/gerrit/chromium-review.googlesource.com/456789/12'
          ),
          experiments=experiments,
      )
    else:
      test += self.m.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder=buildername,
          git_ref=git_ref,
          build_number=571,
          revision='deadbeef'*5,
          tags=self.m.buildbucket.tags(
              user_agent='luci-scheduler',
              buildset='commit/gitiles/chromium.googlesource.com/v8/v8/+/'
                       'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'
          ),
          experiments=experiments,
      )

    # If use_goma is provided (not None), check if relevant steps either are
    # executed or not executed.
    goma_steps = [
      'initialization.ensure_goma',
      'build.preprocess_for_goma',
      'build.postprocess_for_goma'
    ]
    if kwargs.get('use_goma') is True:
      test += self.post_process(MustRun, *goma_steps)
    elif kwargs.get('use_goma') is False:
      test += self.post_process(DoesNotRun, *goma_steps)

    # Skip some goma and swarming related steps in expectations.
    test += self.hide_infra_steps()

    # Only show the command for swarming trigger steps (i.e. drop logs).
    # List of (step-name regexp, tuple of fields to keep).
    keep_fields_spec = [
      ('trigger tests.\[trigger\].*', ('cmd',)),
    ]

    # TODO(machenbach): Add a better field/step dropping mechanism to the
    # engine.
    def keep_fields(_, steps):
      to_ret = OrderedDict()
      for name, step in steps.items():
        for rx, fields in keep_fields_spec:
          if re.match(rx, name):
            to_ret[name] = {
              k: v for k, v in step.to_step_dict().items()
              if k in fields or k == 'name'
            }
            break
        else:
          to_ret[name] = step
      return to_ret

    test += self.post_process(keep_fields)
    return test

  def fail(self, step_name, variant1='default', variant2='default'):
    return self.override_step_data(
        step_name, self.failures_example(variant1=variant1, variant2=variant2))

  @staticmethod
  def _check_step(check, steps, step):
    return check(step in steps)

  @staticmethod
  def _get_param(check, steps, step, param, action=None):
    """Returns the value of the given step's cmd-line parameter."""
    check(step in steps)
    parser = argparse.ArgumentParser()
    # TODO(machenbach): Add test case for this branch or delete code.
    if action:  # pragma: no cover
      parser.add_argument(param, dest='param', action=action)
    else:
      parser.add_argument(param, dest='param')
    options, _ = parser.parse_known_args(steps[step].cmd)
    check(options)
    return options.param

  @staticmethod
  def _check_param_equals(check, steps, step, param, value):
    action = 'store_true' if value in [True, False] else None
    check(value == V8TestApi._get_param(check, steps, step, param, action))

  @staticmethod
  def _check_in_param(check, steps, step, param, value):
    check(value in V8TestApi._get_param(check, steps, step, param))

  def check_param_equals(self, step, param, value):
    """Check if a step has a particular parameter matching a given value."""
    return self.post_process(
        V8TestApi._check_param_equals, step, param, value)

  def check_in_param(self, step, param, value):
    """Check if a given value is a substring of a step's parameter."""
    return self.post_process(V8TestApi._check_in_param, step, param, value)

  def check_in_any_arg(self, step, value):
    """Check if a given value is a substring of any argument in a step."""
    def check_any(check, steps, step, value):
      if self._check_step(check, steps, step):
        check(any(value in arg for arg in steps[step].cmd))
    return self.post_process(check_any, step, value)

  def check_not_in_any_arg(self, step, value):
    """Check that a given value is not a substring of any argument in a step.

    This is the opposite of the method above.
    """
    def check_any(check, steps, step, value):
      if self._check_step(check, steps, step):
        check(not any(value in arg for arg in steps[step].cmd))
    return self.post_process(check_any, step, value)
