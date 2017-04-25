# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'filter',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]


def RunSteps(api):
  api.chromium_tests.trybot_steps()
  assert api.chromium_tests.is_precommit_mode()


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data(
          'read test spec (chromium.linux.json)',
          api.json.output({
              'Linux Tests': {
                  'gtest_tests': ['base_unittests'],
              },
          })
      ) +
      api.filter.suppress_analyze()
  )

  yield (
      api.test('analyze_compile_mode') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_clobber_rel_ng')
  )

  yield (
      api.test('no_compile') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng')
  )

  yield (
      api.test('no_compile_no_source') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('OWNERS')
      )
  )

  yield (
      api.test('blink_linux') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('third_party/WebKit/foo.cc')
      )
  )

  yield (
      api.test('blink_mac') +
      api.platform.name('mac') +
      api.properties.tryserver(
          mastername='tryserver.chromium.mac',
          buildername='mac_chromium_rel_ng') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('third_party/WebKit/foo.cc')
      )
  )
