# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'raw_io',
  'rietveld',
  'step',
  'step_history',
  'test_utils',
]


BUILDERS = {
  'tryserver.blink': {
    'builders': {
      'linux_blink_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'mac_blink_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'win_blink_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'win',
        },
      },
    },
  },
  'tryserver.chromium': {
    'builders': {
      'linux_blink': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_compile': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'mac_blink': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_compile': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'win_blink': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_compile': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'win',
        },
      },
    },
  },
}


def GenSteps(api):
  class BlinkTest(api.test_utils.Test):
    name = 'webkit_tests'

    def __init__(self):
      self.results_dir = api.path['slave_build'].join('layout-test-results')
      self.layout_test_wrapper = api.path['build'].join(
          'scripts', 'slave', 'chromium', 'layout_test_wrapper.py')

    def run(self, suffix):
      args = ['--target', api.chromium.c.BUILD_CONFIG,
              '-o', self.results_dir,
              '--build-dir', api.chromium.c.build_dir,
              '--json-test-results', api.json.test_results()]
      if suffix == 'without patch':
        test_list = "\n".join(self.failures('with patch'))
        args.extend(['--test-list', api.raw_io.input(test_list)])

      def followup_fn(step_result):
        r = step_result.json.test_results
        p = step_result.presentation

        p.step_text += api.test_utils.format_step_text([
          ['unexpected_flakes:', r.unexpected_flakes.keys()],
          ['unexpected_failures:', r.unexpected_failures.keys()],
          ['Total executed: %s' % r.num_passes],
        ])

        if r.unexpected_flakes or r.unexpected_failures:
          p.status = 'WARNING'
        else:
          p.status = 'SUCCESS'

      yield api.chromium.runtest(self.layout_test_wrapper,
                                 args,
                                 name=self._step_name(suffix),
                                 can_fail_build=False,
                                 followup_fn=followup_fn)

      if suffix == 'with patch':
        buildername = api.properties['buildername']
        buildnumber = api.properties['buildnumber']
        def archive_webkit_tests_results_followup(step_result):
          base = (
            "https://storage.googleapis.com/chromium-layout-test-archives/%s/%s"
            % (buildername, buildnumber))

          step_result.presentation.links['layout_test_results'] = (
              base + '/layout-test-results/results.html')
          step_result.presentation.links['(zip)'] = (
              base + '/layout-test-results.zip')

        archive_layout_test_results = api.path['build'].join(
            'scripts', 'slave', 'chromium', 'archive_layout_test_results.py')

        yield api.python(
          'archive_webkit_tests_results',
          archive_layout_test_results,
          [
            '--results-dir', self.results_dir,
            '--build-dir', api.chromium.c.build_dir,
            '--build-number', buildnumber,
            '--builder-name', buildername,
            '--gs-bucket', 'gs://chromium-layout-test-archives',
          ] + api.json.property_args(),
          followup_fn=archive_webkit_tests_results_followup
        )

    def has_valid_results(self, suffix):
      sn = self._step_name(suffix)
      return api.step_history[sn].json.test_results.valid

    def failures(self, suffix):
      sn = self._step_name(suffix)
      return api.step_history[sn].json.test_results.unexpected_failures

  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)

  api.chromium.set_config('blink',
                          **bot_config.get('chromium_config_kwargs', {}))
  api.chromium.apply_config('trybot_flavor')
  api.gclient.set_config('blink_internal')
  api.step.auto_resolve_conflicts = True

  webkit_lint = api.path['build'].join('scripts', 'slave', 'chromium',
                                       'lint_test_files_wrapper.py')
  webkit_python_tests = api.path['build'].join('scripts', 'slave', 'chromium',
                                               'test_webkitpy_wrapper.py')

  root = api.rietveld.calculate_issue_root()

  yield api.gclient.checkout(revert=True)
  steps = [
    api.rietveld.apply_issue(root),
    api.chromium.runhooks(),
    api.chromium.compile(),
  ]

  if not bot_config['compile_only']:
    steps.extend([
      api.python('webkit_lint', webkit_lint, [
        '--build-dir', api.path['checkout'].join('out'),
        '--target', api.chromium.c.BUILD_CONFIG
      ]),
      api.python('webkit_python_tests', webkit_python_tests, [
        '--build-dir', api.path['checkout'].join('out'),
        '--target', api.chromium.c.BUILD_CONFIG,
      ]),
      api.chromium.runtest('webkit_unit_tests', xvfb=True),
      api.chromium.runtest('blink_platform_unittests'),
      api.chromium.runtest('blink_heap_unittests'),
      api.chromium.runtest('wtf_unittests'),
    ])

  yield steps

  if not bot_config['compile_only']:
    def deapply_patch_fn(failing_steps):
      yield (
        api.gclient.revert(),
        api.chromium.runhooks(),
        api.chromium.compile(),
      )

    yield api.test_utils.determine_new_failures([BlinkTest()], deapply_patch_fn,
                                                max_failures=75)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.json.canned_test_output
  with_patch = 'webkit_tests (with patch)'
  without_patch = 'webkit_tests (without patch)'

  def properties(mastername, buildername, **kwargs):
    return api.properties.tryserver(mastername=mastername,
                                    buildername=buildername,
                                    root='src/third_party/WebKit',
                                    **kwargs)

  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                  _sanitize_nonalpha(buildername))
      tests = []
      if bot_config['compile_only']:
        tests.append(api.test(test_name))
      else:
        for pass_first in (True, False):
          test = (
            api.test(test_name + ('_pass' if pass_first else '_fail')) +
            api.step_data(with_patch, canned_test(passing=pass_first))
          )
          if not pass_first:
            test += api.step_data(
                without_patch, canned_test(passing=False, minimal=True))
          tests.append(test)

      for test in tests:
        test += (
          properties(mastername, buildername) +
          api.platform(bot_config['testing']['platform'],
                       bot_config.get(
                           'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
        )

        yield test

  # This tests that if the first fails, but the second pass succeeds
  # that we fail the whole build.
  yield (
    api.test('minimal_pass_continues') +
    properties('tryserver.chromium', 'linux_blink_rel') +
    api.override_step_data(with_patch, canned_test(passing=False)) +
    api.override_step_data(without_patch,
                           canned_test(passing=True, minimal=True))
  )

  yield (
    api.test('bad_revert_bails') +
    properties('tryserver.chromium', 'linux_blink_rel') +
    api.step_data('gclient revert', retcode=1)
  )

  yield (
    api.test('bad_sync_bails') +
    properties('tryserver.chromium', 'linux_blink_rel') +
    api.step_data('gclient sync', retcode=1)
  )
