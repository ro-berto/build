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
# work without making buildbot-side changes. Each builder will only
# have a tag specifying a config/flavor (adding, removing or changing
# builders requires a buildbot-side change anyway), but we can change
# everything about what that config means in the recipe.
RECIPE_CONFIGS = {
  'official': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
}


def GenSteps(api):
  recipe_config_name = api.properties.get('recipe_config')
  if recipe_config_name not in RECIPE_CONFIGS:  # pragma: no cover
    raise ValueError('Unsupported recipe_config "%s"' % recipe_config_name)
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.chromium.set_config(recipe_config['chromium_config'])
  api.gclient.set_config(recipe_config['gclient_config'])
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  yield (
    api.gclient.checkout(),
    api.chromium.runhooks(),
    api.chromium.cleanup_temp(),
    api.chromium.compile(),
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
    api.test('fail') +
    api.properties(recipe_config='official') +
    api.step_data('compile', retcode=1)
  )
