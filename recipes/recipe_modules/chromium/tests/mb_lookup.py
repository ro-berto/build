# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'recipe_engine/assertions',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARDS=api.properties.get('target_cros_boards'))

  gn_args = api.chromium.mb_lookup(
      chromium.BuilderId.create_for_group('test-group', 'test-builder'),
      recursive=api.properties.get('recursive', False),
      use_goma=api.properties.get('use_goma', True),
      use_reclient=api.properties.get('use_reclient', False))
  expected_gn_args = api.properties.get('expected_gn_args')
  api.assertions.assertEqual(gn_args, expected_gn_args)

def GenTests(api):
  gn_args = '\n'.join((
      'goma_dir = "/b/build/slave/cache/goma_client"',
      'target_cpu = "x86"',
      'target_sysroot = "//build/linux"',
      'use_goma = true',
  ))
  expected_step_text = [
      '<br/>'.join(('target_cpu = "x86"', 'use_goma = true')),
      '<br/>'.join((
          'goma_dir = "/b/build/slave/cache/goma_client"',
          'target_sysroot = "//build/linux"'))
  ]

  gn_args_reclient = '\n'.join((
      'goma_dir = "/b/build/slave/cache/goma_client"',
      'target_cpu = "x86"',
      'target_sysroot = "//build/linux"',
      'use_reclient = true',
  ))
  expected_step_text_reclient = [
      '<br/>'.join(('target_cpu = "x86"', 'use_reclient = true')), '<br/>'.join(
          ('goma_dir = "/b/build/slave/cache/goma_client"',
           'target_sysroot = "//build/linux"'))
  ]

  yield api.test(
      'basic',
      api.properties(expected_gn_args=gn_args),
      api.step_data('lookup GN args', stdout=api.raw_io.output_text(gn_args)),
      api.post_process(post_process.StepCommandContains, 'lookup GN args',
                       ['--quiet']),
      api.post_process(post_process.StepTextContains, 'lookup GN args',
                       expected_step_text),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic_reclient',
      api.properties(use_reclient=True, use_goma=False),
      api.properties(expected_gn_args=gn_args_reclient),
      api.step_data(
          'lookup GN args', stdout=api.raw_io.output_text(gn_args_reclient)),
      api.post_process(post_process.StepCommandContains, 'lookup GN args',
                       ['--quiet']),
      api.post_process(post_process.StepTextContains, 'lookup GN args',
                       expected_step_text_reclient),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cros_boards',
      api.properties(
          target_platform='chromeos', target_cros_boards='x86-generic'),
      api.properties(expected_gn_args=gn_args),
      api.step_data('lookup GN args', stdout=api.raw_io.output_text(gn_args)),
      api.post_process(post_process.StepCommandContains, 'lookup GN args',
                       ['--quiet']),
      api.post_process(post_process.StepTextContains, 'lookup GN args',
                       expected_step_text),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'recursive',
      api.properties(expected_gn_args=gn_args, recursive=True),
      api.step_data('lookup GN args', stdout=api.raw_io.output_text(gn_args)),
      api.post_process(post_process.StepCommandContains, 'lookup GN args',
                       ['--recursive']),
      api.post_process(post_process.StepTextContains, 'lookup GN args',
                       expected_step_text),
      api.post_process(post_process.DropExpectation),
  )
