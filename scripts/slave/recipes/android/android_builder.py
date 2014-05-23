# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_android',
  'properties',
]

BUILDERS = {
  'Android ARM64 Builder (dbg)': {
    'recipe_config': 'arm64_builder',
  },
  'Android x64 Builder (dbg)': {
    'recipe_config': 'x64_builder',
  },
  'Android MIPS Builder (dbg)': {
    'recipe_config': 'mipsel_builder',
  }
}

def GenSteps(api):
  buildername = api.properties['buildername']
  bot_config = BUILDERS[buildername]
  droid = api.chromium_android

  default_kwargs = {
    'REPO_URL': 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src',
    'INTERNAL': False,
    'REPO_NAME': 'src',
    'BUILD_CONFIG': 'Debug'
  }
  droid.configure_from_properties(bot_config['recipe_config'], **default_kwargs)
  droid.c.set_val({'deps_file': 'DEPS'})

  yield droid.init_and_sync()
  yield droid.clean_local_files()
  yield droid.runhooks()
  yield droid.compile()
  yield droid.cleanup_build()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

def GenTests(api):
  # tests bots in BUILDERS
  for buildername in BUILDERS:
    yield (
      api.test('full_%s' % _sanitize_nonalpha(buildername)) +
      api.properties.generic(buildername=buildername,
          repository='svn://svn.chromium.org/chrome/trunk/src',
          buildnumber=257,
          mastername='chromium.fyi',
          revision='267739'))
