# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'filter',
  'recipe_engine/platform',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config(
    'chromium_chromeos',
    TARGET_PLATFORM='chromeos',
    TARGET_CROS_BOARD='x86=generic')
  api.chromium.apply_config('mb')

  api.filter.analyze(
      ['file1', 'file2'],
      ['test1', 'test2'],
      ['compile1', 'compile2'],
      'config.json',
      mb_mastername=api.properties.get('mastername'),
      mb_buildername=api.properties.get('buildername'),
      mb_config_path=api.properties.get('mb_config_path'))


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          config='cros')
  )

  def command_line_contains(check, step_odict, step_name, argument_sequence):
    def subsequence(containing, contained):
      for i in xrange(len(containing) - len(contained)):
        if containing[i:i+len(contained)] == contained:
          return True
      return False  # pragma: no cover

    check('No step named "%s"' % step_name,
          step_name in step_odict)
    check('Command line for step "%s" did not contain "%s"' % (
              step_name, ' '.join(argument_sequence)),
          subsequence(step_odict[step_name]['cmd'], argument_sequence))
    return step_odict

  yield (
      api.test('custom_mb_config_path') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          mb_config_path='path/to/custom_mb_config.pyl',
          config='cros') +
      api.post_process(command_line_contains,
                       step_name='analyze',
                       argument_sequence=[
                           '-f', 'path/to/custom_mb_config.pyl']) +
      api.post_process(post_process.DropExpectation)
  )
