# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'json',
  'platform',
  'properties',
  'v8',
]


V8_TEST_CONFIGS = {
  'mozilla': {
    'name': 'Mozilla',
    'tests': 'mozilla',
    'flaky_step': False,
    'gclient_apply_config': ['mozilla_tests'],
  },
  'test262': {
    'name': 'Test262',
    'tests': 'test262',
    'flaky_step': False,
  },
  'v8testing': {
    'name': 'Check',
    'tests': 'mjsunit cctest message preparser',
    'flaky_step': True,
  },
  'webkit': {
    'name': 'Webkit',
    'tests': 'webkit',
    'flaky_step': True,
  },
}


class V8Test(object):
  def __init__(self, name):
    self.name = name

  def run(self, api):
    return api.v8.runtest(V8_TEST_CONFIGS[self.name])

  def gclient_apply_config(self):
    return V8_TEST_CONFIGS[self.name].get('gclient_apply_config', [])


BUILDERS = {
  'client.v8': {
    'builders': {
      'V8 Linux - shared': {
        'recipe_config': 'v8',
        'chromium_apply_config': ['shared_library'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          V8Test('v8testing'),
          V8Test('test262'),
          V8Test('mozilla'),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      # This builder is used as a staging area for builders on the main
      # waterfall to be switched to recipes.
      'V8 Linux - recipe': {
        'recipe_config': 'v8',
        'gclient_apply_config': ['clang'],
        'chromium_apply_config': ['clang'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          V8Test('v8testing'),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
}

RECIPE_CONFIGS = {
  'v8': {
    'v8_config': 'v8',
  },
}

def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  assert recipe_config_name, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.v8.set_config(recipe_config['v8_config'],
                    optional=True,
                    **bot_config.get('v8_config_kwargs', {}))

  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)

  # Test-specific configurations.
  for t in bot_config.get('tests', []):
    for c in t.gclient_apply_config():
      api.gclient.apply_config(c)

  yield api.v8.checkout()
  steps = [api.v8.runhooks()]

  if 'clang' in bot_config.get('gclient_apply_config', []):
    steps.append(api.v8.update_clang())

  steps.append(api.v8.compile())
  steps.extend([t.run(api) for t in bot_config.get('tests', [])])
  yield steps


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config['testing'].get('parent_buildername') is None

      v8_config_kwargs = bot_config.get('v8_config_kwargs', {})
      test = (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties(mastername=mastername,
                       buildername=buildername) +
        api.platform(bot_config['testing']['platform'],
                     v8_config_kwargs.get('TARGET_BITS', 64))
      )

      yield test
