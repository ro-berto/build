# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetSteps(api):
  api.set_common_configuration('blink')
  api.auto_resolve_conflicts = True

  script = ['python', api.build_path('scripts', 'slave', 'chromium',
                                     'layout_test_wrapper.py')]
  final_script = [
      'python',
      api.checkout_path('third_party', 'WebKit', 'Tools', 'Scripts',
                        'print-json-test-results')]

  webkit_lint = api.build_path('scripts', 'slave', 'chromium',
                               'lint_test_files_wrapper.py')

  def BlinkTestsStep(with_patch):
    name = 'webkit_tests (with%s patch)' % ('' if with_patch else 'out')
    return api.step(name, script, add_json_output=True, can_fail_build=False)

  def generator(step_history, _failure):
    yield (
      api.gclient_checkout('blink'),
      api.apply_issue(),
      api.gclient_runhooks(),
      api.chromium_compile(),
      api.runtests('webkit_unit_tests'),
      api.step('webkit_lint', [
        'python', webkit_lint, '--build-dir', api.checkout_path('out'),
        '--target', api.properties['build_config']]),
    )

    yield BlinkTestsStep(with_patch=True)
    if step_history.last_step().retcode == 0:
      yield api.step('webkit_tests', ['python', '-e', 'print "ALL IS WELL"'])
      return

    failing_tests = step_history.last_step().json_data

    yield (
      api.gclient_revert(),
      api.gclient_runhooks(),
      api.chromium_compile(),
      BlinkTestsStep(with_patch=False),
    )
    base_failing_tests = step_history.last_step().json_data

    yield api.step('webkit_tests', final_script + [
      '--ignored-failures-path', api.json_input(base_failing_tests),
      api.json_input(failing_tests),
    ])

  return generator