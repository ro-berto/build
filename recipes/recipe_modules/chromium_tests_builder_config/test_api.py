# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from RECIPE_MODULES.build.chromium import BuilderId

from . import builders, trybots, BuilderConfig, BuilderDatabase, TryDatabase


class ChromiumTestsBuilderConfigApi(recipe_test_api.RecipeTestApi):

  @staticmethod
  def _get_builder_id(builder_group, builder, **_):
    return BuilderId.create_for_group(builder_group, builder)

  # TODO(gbeaty) After migration to python3 is complete, change the signature to
  # (*, use_try_db, builder_db=None, try_db=None)
  @staticmethod
  def _get_databases(use_try_db, **kwargs):
    if 'builder_db' in kwargs:
      builder_db = kwargs.pop('builder_db')
      if use_try_db:
        assert 'try_db' in kwargs, (
            'If using try_db, '
            'try_db must be specified when specifying builder_db')
      try_db = kwargs.pop('try_db', None) or TryDatabase.create({})

    else:
      assert not 'try_db' in kwargs, (
          'Cannot specify try_db without specifying builder_db')
      builder_db = builders.BUILDERS
      try_db = trybots.TRYBOTS

    return builder_db, try_db, use_try_db, kwargs

  # TODO(gbeaty) After migration to python3 is complete, change the signature to
  # (*, builder_group, builder, use_try_db, builder_db=None, try_db=None)
  def _test_data(self, **kwargs):
    builder_id = self._get_builder_id(**kwargs)
    builder_db, try_db, use_try_db, kwargs = self._get_databases(**kwargs)

    builder_config = BuilderConfig.lookup(builder_id, builder_db,
                                          try_db if use_try_db else None)

    test_data = sum([
        self.builder_db(builder_db),
        self.try_db(try_db),
        self.m.platform(
            builder_config.simulation_platform or 'linux',
            builder_config.chromium_config_kwargs.get('TARGET_BITS', 64)),
    ], self.empty_test_data())

    return test_data, kwargs

  def generic_build(self, **kwargs):
    """Create test data for a generic build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium and
    chromium_tests_builder_config modules for builds that have neither
    an associated gitiles commit or gerrit change (e.g. CI builder
    triggered via the scheduler UI or a cron-like schedule).

    All keyword arguments supported by chromium.generic_build are
    supported, as well as the following additional keyword arguments:
    * builder_db - Overrides the default builder database.
    * try_db - Override the default try database. Can only be specified
      if builder_db is also specified. If builder_db is specified and
      try_db is not specified, an empty try database will be used as the
      default try database.
    * use_try_db - Whether the try_db should be used for looking up the
      builder to set the platform.
    """
    kwargs.setdefault('builder', 'Linux Builder')
    kwargs.setdefault('builder_group', 'chromium.linux')
    kwargs.setdefault('use_try_db', False)
    ctbc_test_data, kwargs = self._test_data(**kwargs)
    return self.m.chromium.generic_build(**kwargs) + ctbc_test_data

  def ci_build(self, **kwargs):
    """Create test data for a CI build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium and
    chromium_tests_builder_config modules for builds that would be
    triggered by a scheduler poller with an associated gitiles commit
    (or triggered by another builder that was triggered by a scheduler
    poller).

    All keyword arguments supported by chromium.generic_build are
    supported, as well as the following additional keyword arguments:
    * builder_db - Overrides the default builder database.
    * try_db - Override the default try database. Can only be specified
      if builder_db is also specified. If builder_db is specified and
      try_db is not specified, an empty try database will be used as the
      default try database.
    """
    assert 'use_try_db' not in kwargs
    kwargs.setdefault('builder', 'Linux Builder')
    kwargs.setdefault('builder_group', 'chromium.linux')
    ctbc_test_data, kwargs = self._test_data(use_try_db=False, **kwargs)
    return self.m.chromium.ci_build(**kwargs) + ctbc_test_data

  def try_build(self, **kwargs):
    """Create test data for a try build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium and
    chromium_tests_builder_config modules for try builds with an
    associated gerrit change.

    All keyword arguments supported by chromium.generic_build are
    supported, as well as the following additional keyword arguments:
    * builder_db - Overrides the default builder database.
    * try_db - Override the default try database. Can only be specified
      if builder_db is also specified. If builder_db is specified and
      try_db is not specified, an empty try database will be used as the
      default try database.
    """
    assert 'use_try_db' not in kwargs
    kwargs.setdefault('builder', 'linux-rel')
    kwargs.setdefault('builder_group', 'tryserver.chromium.linux')
    ctbc_test_data, kwargs = self._test_data(use_try_db=True, **kwargs)
    return self.m.chromium.try_build(**kwargs) + ctbc_test_data

  # TODO(https://crbug.com/1193832) Switch callers to use (generic|ci|try)_build
  @recipe_test_api.mod_test_data
  @staticmethod
  def builder_db(builder_db):
    """Override the default BuilderDatabase for a test.

    Generally (generic|ci|try)_build should be preferred instead, use
    this only for tests of recipes that directly access
    chromium_tests_builder_config.builder_db.

    Args:
      * builder_db - A BuilderDatabase to replace
        chromium_tests_builder_config.builder_db.
    """
    assert isinstance(builder_db, BuilderDatabase)
    return builder_db

  @recipe_test_api.mod_test_data
  @staticmethod
  def try_db(try_db):
    """Override the default TryDatabase for a test.

    Generally (generic|ci|try)_build should be preferred instead, use
    this only for tests of recipes that directly access
    chromium_tests_builder_config.try_db.

    Args:
      * try_db - A TryDatabase to replace
        chromium_tests_builder_config.try_db.
    """
    assert try_db is None or isinstance(try_db, TryDatabase)
    return try_db
