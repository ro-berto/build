# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

from . import builders, trybots, BuilderConfig


class ChromiumTestsBuilderConfigApi(recipe_api.RecipeApi):

  def __init__(self, **kwargs):
    super(ChromiumTestsBuilderConfigApi, self).__init__(**kwargs)
    self._builder_db = builders.BUILDERS
    self._try_db = trybots.TRYBOTS
    if self._test_data.enabled:
      if 'builder_db' in self._test_data:
        self._builder_db = self._test_data['builder_db']
      if 'try_db' in self._test_data:
        self._try_db = self._test_data['try_db']

  @property
  def builder_db(self):
    return self._builder_db

  @property
  def try_db(self):
    return self._try_db

  def lookup_builder(self,
                     builder_id=None,
                     builder_db=None,
                     try_db=None,
                     use_try_db=None,
                     builder_config_class=None):
    """Lookup a builder, getting the matching bot config.

    Args:
      * builder_id - The BuilderId identifying the builder to get a
        BuilderConfig for. By default, self.m.chromium.get_builder_id()
        will be used.
      * builder_db - The BuilderDatabase to look for BuilderSpecs in. By
        default, self.builder_db will be used.
      * try_db - The TryDatabase to look for TrySpecs in. By Default,
        self.trybots will be used.
      * use_try_db - Whether or not to look for TrySpecs in try_db. If
        try_db is used, and it contains a TrySpec for the builder
        identified by builder_id, the BuilderConfig will wrap the
        BuilderSpecs for the builders identified by the mirrors of the
        TrySpec. Otherwise, the BuilderConfig will wrap the BuilderSpec
        for the builder identified by builder_id. By default, the try_db
        will be used if self.m.tryserver.is_tryserver is True.
      * builder_config_class - The class of the builder config to
        create. If not provided, BuilderConfig will be used. The class
        must have a lookup method that takes the builder_id, builder_db
        and try_db as positional arguments and keyword arguments
        use_try_db and step_api. use_try_db acts as indicated above.
        step_api is the API object for the step recipe module and
        should be used for creating an infra failing step if creation of
        the builder config fails.

    Returns: A 2-tuple: * The BuilderId of the builder the BuilderConfig
      is for. * The BuilderConfig for the builder.
    """
    builder_id = builder_id or self.m.chromium.get_builder_id()

    if builder_db is None:
      assert try_db is None
      builder_db = self.builder_db
      try_db = self.try_db

    if use_try_db is None:
      use_try_db = self.m.tryserver.is_tryserver

    builder_config_class = builder_config_class or BuilderConfig
    builder_config = builder_config_class.lookup(
        builder_id,
        builder_db,
        try_db,
        use_try_db=use_try_db,
        step_api=self.m.step)
    return builder_id, builder_config
