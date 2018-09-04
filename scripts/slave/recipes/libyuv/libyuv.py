# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for building and running tests for Libyuv stand-alone.
"""

from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'chromium_android',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'libyuv',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
]


def RunSteps(api):
  libyuv = api.libyuv
  libyuv.apply_bot_config(libyuv.BUILDERS, libyuv.RECIPE_CONFIGS)

  libyuv.checkout()
  if libyuv.should_build:
    api.chromium.ensure_goma()
  api.chromium.runhooks()

  if libyuv.should_build:
    api.chromium.run_gn(use_goma=True)
    api.chromium.compile(use_goma_module=True)
    if libyuv.should_upload_build:
      libyuv.package_build()

  if libyuv.should_download_build:
    libyuv.extract_build()

  if libyuv.should_test:
    libyuv.runtests()

  libyuv.maybe_trigger()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  builders = api.libyuv.BUILDERS

  def generate_builder(
        mastername, buildername, revision, suffix=None, buildbot=False):
    suffix = suffix or ''
    bot_config = builders[mastername]['builders'][buildername]
    bot_type = bot_config.get('bot_type', 'builder_tester')

    chromium_kwargs = bot_config.get('chromium_config_kwargs', {})
    test = api.test('%s_%s%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername), suffix))

    if mastername.startswith('tryserver'):
      test += api.properties.tryserver(gerrit_project='libyuv')

    test += api.properties(
        mastername=mastername,
        buildername=buildername,
        bot_id='bot_id',
        BUILD_CONFIG=chromium_kwargs['BUILD_CONFIG'])
    test += api.platform(bot_config['testing']['platform'],
                         chromium_kwargs.get('TARGET_BITS', 64))
    test += api.runtime(is_experimental=False, is_luci=not buildbot)

    if bot_config.get('parent_buildername'):
      test += api.properties(
          parent_buildername=bot_config['parent_buildername'])

    if revision:
      test += api.properties(revision=revision)
    if bot_type == 'tester':
      test += api.properties(parent_got_revision=revision)

    test += api.properties(buildnumber=1337)
    return test

  for mastername, master_config in builders.iteritems():
    for buildername in master_config['builders'].keys():
      yield generate_builder(mastername, buildername, revision='a' * 40)

  # Forced builds (not specifying any revision) and test failures.
  mastername = 'client.libyuv'
  yield generate_builder(mastername, 'Linux64 Debug', revision=None,
                         suffix='_forced')
  yield generate_builder(mastername, 'Android Debug', revision=None,
                         suffix='_buildbot', buildbot=True)
  yield generate_builder(mastername, 'Android Debug', revision=None,
                         suffix='_forced')
  yield generate_builder(mastername, 'Android Tester ARM32 Debug (Nexus 5X)',
                         revision=None, suffix='_forced_invalid')
  yield generate_builder(mastername, 'iOS Debug', revision=None,
                         suffix='_forced')

  yield generate_builder('tryserver.libyuv', 'linux', revision=None,
                         suffix='_forced')
