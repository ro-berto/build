# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

import re

from recipe_engine import recipe_test_api
from . import builders
from . import testing

# Simulated branch names for testing. Optionally upgrade these in branch
# period to reflect the real branches used by the gitiles poller.
STABLE_BRANCH = '4.2'
BETA_BRANCH = '4.3'


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


class V8TestApi(recipe_test_api.RecipeTestApi):
  BUILDERS = builders.BUILDERS

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

  def iter_builders(self):
    return builders.iter_builders()

  def output_json(self, has_failures=False, wrong_results=False, flakes=False,
                  unmarked_slow_test=False):
    slowest_tests = V8TestApi.SLOWEST_TESTS()
    if unmarked_slow_test:
      slowest_tests += [{
        'name': 'mjsunit/slow',
        'flags': [],
        'command': 'd8 -f mjsunit/slow',
        'duration': 123.0,
        'marked_slow': False,
      }]
    if not has_failures:
      return self.m.json.output([{
        'arch': 'theArch',
        'mode': 'theMode',
        'results': [],
        'slowest_tests': slowest_tests,
      }])
    if wrong_results:
      return self.m.json.output([{
        'arch': 'theArch1',
        'mode': 'theMode1',
        'results': [],
        'slowest_tests': slowest_tests,
      },
      {
        'arch': 'theArch2',
        'mode': 'theMode2',
        'results': [],
        'slowest_tests': slowest_tests,
      }])
    if flakes:
      return self.m.json.output([{
        'arch': 'theArch1',
        'mode': 'theMode1',
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
      }])


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
        'name': 'other-suite/dir/other-test-very-long-name%d' % i,
        'command': ('out/theMode/d8 --other '
                    'test/other-suite/dir/other-test-very-long-name.js'),
        'exit_code': 1,
      })

    return self.m.json.output([{
      'arch': 'theArch',
      'mode': 'theMode',
      'results': results,
      'slowest_tests': slowest_tests,
    }])

  def one_failure(self):
    return self.m.json.output([{
      'arch': 'theArch',
      'mode': 'theMode',
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
    }])

  def failures_example(self, variant='default'):
    return self.m.json.output([{
      'arch': 'theArch',
      'mode': 'theMode',
      'results': [
        {
          'flags': [],
          'result': 'FAIL',
          'expected': ['PASS', 'SLOW'],
          'duration': 3,
          'variant': variant,
          'random_seed': 123,
          'run': 1,
          'stdout': 'Some output.',
          'stderr': 'Some errput.',
          'name': 'suite-name/dir/slow',
          'command': 'd8 test.js',
          'target_name': 'd8',
          'exit_code': 1,
        },
        {
          'flags': [],
          'result': 'FAIL',
          'expected': ['PASS', 'SLOW'],
          'duration': 1.5,
          'variant': variant,
          'random_seed': 123,
          'run': 1,
          'stdout': 'Some output.',
          'stderr': 'Some errput.',
          'name': 'suite-name/dir/fast',
          'command': 'd8 test.js',
          'target_name': 'd8',
          'exit_code': 1,
        },
      ],
      'slowest_tests': V8TestApi.SLOWEST_TESTS(),
    }])

  def example_buildbot_changes(self):
    return self.m.json.output({
      'sourceStamp': {
        'changes': [
          {'revision': 'a1'},
          {'revision': 'a2'},
          {'revision': 'a3'},
        ]
      }
    })

  def example_one_buildbot_change(self):
    return self.m.json.output({
      'sourceStamp': {
        'changes': [
          {'revision': 'a1'},
        ]
      }
    })

  def example_bisection_range(self):
    # Gitiles returns changes in the order newest -> oldest.
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
    return self.m.raw_io.stream_output(
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

  def _get_test_branch_name(self, mastername, buildername):
    if mastername == 'client.dart.fyi':
      return STABLE_BRANCH
    if re.search(r'stable branch', buildername):
      return STABLE_BRANCH
    if re.search(r'beta branch', buildername):
      return BETA_BRANCH
    return 'master'

  def _make_dummy_swarm_hashes(self, bot_config):
    """Makes dummy isolate hashes for all tests of a bot.

    Either an explicit isolate target must be defined or the naming
    convention "test name == isolate target name" will be used.
    """
    def gen_isolate_targets(test_config):
      config = testing.TEST_CONFIGS.get(test_config.name, {})
      if config.get('isolated_target'):
        yield config['isolated_target']
      else:
        for test in config.get('tests', []):
          yield test

    return dict(
        (target, '[dummy hash for %s]' % target)
        for test_config in bot_config.get('tests', [])
        for target in gen_isolate_targets(test_config)
    )


  def test(self, mastername, buildername, suffix='', **kwargs):
    name = '_'.join(filter(bool, [
      'full',
      _sanitize_nonalpha(mastername),
      _sanitize_nonalpha(buildername),
      suffix,
    ]))
    builders_list = builders.BUILDERS[mastername]['builders']
    bot_config = builders_list[buildername]
    v8_config_kwargs = bot_config.get('v8_config_kwargs', {})
    parent_buildername = bot_config.get('parent_buildername')
    branch=self._get_test_branch_name(mastername, buildername)

    if bot_config.get('bot_type') in ['builder', 'builder_tester']:
      assert parent_buildername is None

    if mastername.startswith('tryserver'):
      properties_fn = self.m.properties.tryserver
    else:
      properties_fn = self.m.properties.generic

    test = (
        recipe_test_api.RecipeTestApi.test(name) +
        properties_fn(
            mastername=mastername,
            buildername=buildername,
            branch=branch,
            parent_buildername=parent_buildername,
            revision='20123',
            **kwargs
        ) +
        self.m.platform(
            bot_config['testing']['platform'],
            v8_config_kwargs.get('TARGET_BITS', 64),
        )
    )
    if parent_buildername:
      test += self.m.properties(
          # TODO(machenbach): Turn that into a git hash.
          parent_got_revision='54321',
          parent_got_revision_cp='refs/heads/master@{#20123}',
          parent_build_environment={
            'useful': 'envvars', 'from': 'the', 'parent': 'bot'},
      )
      if bot_config.get('enable_swarming'):
        # Assume each tester is triggered with the required hashes for all
        # tests.
        test += self.m.properties(
          parent_got_swarming_client_revision='[dummy swarming client hash]',
          swarm_hashes=self._make_dummy_swarm_hashes(bot_config),
        )

    if mastername.startswith('tryserver'):
      test += self.m.properties(
          category='cq',
          master='tryserver.v8',
          patch_project='v8',
          patch_storage='rietveld',
          reason='CQ',
          revision='12345',
          try_job_key='1234',
      )

    return test

  def fail(self, step_name, variant='default'):
    return self.override_step_data(
        step_name, self.failures_example(variant=variant))
