# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for building and running tests for Libyuv stand-alone.
"""

from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'libyuv',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

def RunSteps(api):
  libyuv = api.libyuv
  libyuv.apply_bot_config(libyuv.BUILDERS, libyuv.RECIPE_CONFIGS)

  api.bot_update.ensure_checkout()
  api.chromium.cleanup_temp()
  api.chromium.ensure_goma()
  api.chromium.runhooks()

  if libyuv.should_build:
    if api.chromium.c.project_generator.tool == 'gn':
      api.chromium.run_gn(use_goma=True)
      api.chromium.compile(targets=['all'])
    else:
      api.chromium.compile()

  if libyuv.should_test:
    api.chromium.runtest('libyuv_unittest')


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  builders = api.libyuv.BUILDERS

  def generate_builder(mastername, buildername, revision, suffix=None):
    suffix = suffix or ''
    bot_config = builders[mastername]['builders'][buildername]

    chromium_kwargs = bot_config.get('chromium_config_kwargs', {})
    test = (
      api.test('%s_%s%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername), suffix)) +
      api.properties(mastername=mastername,
                     buildername=buildername,
                     slavename='slavename',
                     BUILD_CONFIG=chromium_kwargs['BUILD_CONFIG']) +
      api.platform(bot_config['testing']['platform'],
                   chromium_kwargs.get('TARGET_BITS', 64))
    )

    if revision:
      test += api.properties(revision=revision)

    if mastername.startswith('tryserver'):
      test += api.properties(issue='123456789', patchset='1',
                             rietveld='https://rietveld.example.com')
    return test

  for mastername, master_config in builders.iteritems():
    for buildername in master_config['builders'].keys():
      yield generate_builder(mastername, buildername, revision='12345')

  # Forced builds (not specifying any revision) and test failures.
  mastername = 'client.libyuv'
  yield generate_builder(mastername, 'Linux64 Debug', revision=None,
                         suffix='_forced')
  yield generate_builder(mastername, 'Android Debug', revision=None,
                         suffix='_forced')

  yield generate_builder('tryserver.libyuv', 'linux', revision=None,
                         suffix='_forced')
