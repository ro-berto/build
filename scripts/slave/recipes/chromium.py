# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'platform',
  'properties',
  'python',
  'step_history',
]


# Make it easy to change how different configurations of this recipe
# work without making buildbot-side changes. This contains a dictionary
# of buildbot masters, and each of these dictionaries maps a builder name
# to one of recipe configs below.
BUILDERS = {
  'chromium.chrome': {
    'Google Chrome ChromeOS': {
      'recipe_config': 'chromeos_official',
      'compile_targets': [
        'chrome',
        'chrome_sandbox',
        'linux_symbols',
        'symupload'
      ],
    },
    'Google Chrome Linux': {
      'recipe_config': 'official',
    },
    'Google Chrome Linux x64': {
      'recipe_config': 'official',
    },
    'Google Chrome Mac': {
      'recipe_config': 'official',
    },
    'Google Chrome Win': {
      'recipe_config': 'official',
    },
  },
}


# Different types of builds this recipe can do.
RECIPE_CONFIGS = {
  'chromeos_official': {
    'chromium_config': 'chromium_official',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'official': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
}


def GenSteps(api):
  bot_config = {}
  recipe_config_name = api.properties.get('recipe_config')
  if recipe_config_name:
    assert recipe_config_name in RECIPE_CONFIGS, (
        'Unsupported recipe_config "%s"' % recipe_config_name)
  else:
    mastername = api.properties.get('mastername')
    buildername = api.properties.get('buildername')
    bot_config = BUILDERS.get(mastername, {}).get(buildername)
    recipe_config_name = bot_config['recipe_config']
    assert recipe_config_name, (
        'Unrecognized builder name %r for master %r.' % (
            buildername, mastername))
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.chromium.set_config(recipe_config['chromium_config'])
  for c in recipe_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  api.gclient.set_config(recipe_config['gclient_config'])
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  yield (
    api.gclient.checkout(),
    api.chromium.runhooks(),
    api.chromium.cleanup_temp(),
    api.chromium.compile(targets=bot_config.get('compile_targets')),
  )


def GenTests(api):
  for recipe_config in RECIPE_CONFIGS:
    for plat in ('win', 'mac', 'linux'):
      for bits in (32, 64):
        yield (
          api.test('basic_%s_%s_%s' % (recipe_config, plat, bits)) +
          api.properties(recipe_config=recipe_config, TARGET_BITS=bits) +
          api.platform(plat, bits)
        )

  yield (
    api.test('chromium_chrome_google_chrome_linux_x64') +
    api.properties(mastername='chromium.chrome',
                   buildername='Google Chrome Linux x64') +
    api.platform('linux', 64)
  )

  yield (
    api.test('fail') +
    api.properties(recipe_config='official') +
    api.step_data('compile', retcode=1)
  )
