# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
import textwrap

from RECIPE_MODULES.build import chromium

DEPS = [
  'chromium',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/json',
]

def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARD=api.properties.get('target_cros_board'))

  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)

  if api.properties.get('use_explicit_isolate_map_path'):
    api.chromium.c.project_generator.isolate_map_paths = [
        api.path['checkout'].join(
            'testing', 'buildbot', 'gn_isolate_map.pyl')]
  api.chromium.mb_gen(
      chromium.BuilderId.create_for_master('test_mastername',
                                           'test_buildername'),
      phase='test_phase',
      isolated_targets=['base_unittests_run'],
      android_version_code=3,
      android_version_name='example')


def GenTests(api):
  yield api.test('basic')

  yield api.test(
      'cros_board',
      api.properties(
          target_platform='chromeos', target_cros_board='x86-generic'),
  )

  yield api.test(
      'win',
      api.properties(chromium_apply_config=['win_analyze']),
  )

  yield api.test(
      'mac',
      api.platform('mac', 64),
      api.properties(target_platform='mac'),
  )

  yield api.test(
      'explicit_mb',
      api.properties(
          use_explicit_isolate_map_path=True,
          chromium_apply_config=['chromium_official']),
  )

  yield api.test(
      'mac_failure',
      api.platform('mac', 64),
      api.properties(target_platform='mac'),
      api.step_data(
          'generate_build_files',
          api.json.output({
              'output': 'ERROR at line 5: missing )'
          },
                          name="failure_summary"),
          retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(
          post_process.ResultReason,
          textwrap.dedent('''
          #### Step _generate_build_files_ failed. Error logs are shown below:
          ```
          ERROR at line 5: missing )
          ```
          #### More information can be found in the stdout.
      ''').strip()),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'win_failure',
      api.platform('win', 64),
      api.properties(target_platform='win'),
      api.step_data(
          'generate_build_files',
          api.json.output({
              'output': 'ERROR at line 5: missing )'
          },
                          name="failure_summary"),
          retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(
          post_process.ResultReason,
          textwrap.dedent('''
          #### Step _generate_build_files_ failed. Error logs are shown below:
          ```
          ERROR at line 5: missing )
          ```
          #### More information can be found in the stdout.
      ''').strip()),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mb_long_error',
      api.chromium.change_char_size_limit(350),
      api.chromium.change_line_limit(150),
      api.step_data(
          'generate_build_files',
          api.json.output({
              'output':
                  textwrap.dedent("""
                ERROR at //view_unittest.cc:38:11: Can't include header here.
                #include "ui/compositor_extra/shadow.h"
                :          ^---------------------------
                ERROR at //view_unittest.cc:38:12: Can't include header here.
                #include "ui/compositor_extra/shadow2.h"
                ERROR at //view_unittest.cc:38:13: Can't include header here.
                #include "ui/compositor_extra/shadow3.h"
                ERROR at //view_unittest.cc:38:14: Can't include header here.
                #include "ui/compositor_extra/shadow4.h"
              """).strip()
          },
                          name="failure_summary"),
          retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(
          post_process.ResultReason,
          textwrap.dedent("""
          #### Step _generate_build_files_ failed. Error logs are shown below:
          ```
          ERROR at //view_unittest.cc:38:11: Can't include header here.
          #include "ui/compositor_extra/shadow.h"
          :          ^---------------------------
          ERROR at //view_unittest.cc:38:12: Can't include header here.
          #include "ui/compositor_extra/shadow2.h"
          ERROR at //view_unittest.cc:38:13: Can't include header here.
          #include "ui/compositor_extra/shadow3.h"
          ```
          ##### ...The message was too long...
          #### More information can be found in the stdout.
        """).strip()),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mb_luci_auth',
      api.properties(chromium_apply_config=['mb', 'mb_luci_auth']),
      api.post_process(post_process.StepCommandContains, 'generate_build_files',
                       ['--luci-auth']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
