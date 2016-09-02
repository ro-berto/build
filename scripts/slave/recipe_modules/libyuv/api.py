# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from . import builders


class LibyuvApi(recipe_api.RecipeApi):
  BUILDERS = builders.BUILDERS
  RECIPE_CONFIGS = builders.RECIPE_CONFIGS

  def __init__(self, **kwargs):
    super(LibyuvApi, self).__init__(**kwargs)


  def apply_bot_config(self, builders, recipe_configs, perf_config=None):
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = builders.get(mastername, {})

    self.bot_config = master_dict.get('builders', {}).get(buildername)
    assert self.bot_config, ('Unrecognized builder name "%r" for master "%r".' %
                             (buildername, mastername))

    self.bot_type = self.bot_config['bot_type']
    recipe_config_name = self.bot_config['recipe_config']
    self.recipe_config = recipe_configs.get(recipe_config_name)
    assert self.recipe_config, (
        'Cannot find recipe_config "%s" for builder "%r".' %
        (recipe_config_name, buildername))

    chromium_kwargs = self.bot_config.get('chromium_config_kwargs', {})

    self.m.chromium.set_config(self.recipe_config['chromium_config'],
                               **chromium_kwargs)
    self.m.gclient.set_config(self.recipe_config['gclient_config'])

    # Support applying configs both at the bot and the recipe config level.
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    if self.m.tryserver.is_tryserver:
      self.m.chromium.apply_config('trybot_flavor')

  @property
  def should_build(self):
    return self.bot_type in ('builder', 'builder_tester')

  @property
  def should_test(self):
    return self.bot_type in ('tester', 'builder_tester')
