# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from typing import Dict, Optional

from recipe_engine import recipe_test_api

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb
from PB.recipe_modules.build.chromium_polymorphic \
    import properties as properties_pb


class ChromiumPolymorphicTestApi(recipe_test_api.RecipeTestApi):

  def properties_on_target_build(
      self,
      properties: Dict[str, object],
      *,
      step_name: Optional[str] = None,
  ) -> recipe_test_api.StepTestData:
    """Mocks the properties on the most recent build.

    The most recent build is looked up by get_target_properties and the
    target properties are computed based off of the properties on the
    build.
    """
    build = build_pb.Build()
    build.input.properties.update(properties)
    return self.m.buildbucket.simulated_search_results([build],
                                                       step_name=step_name)

  def triggered_properties(
      self,
      *,
      builder_group: str,
      builder: str,
      project: str = 'chromium',
      bucket: str = 'ci',
  ) -> recipe_test_api.TestData:
    """Set properties that would be set for a polymoprhic builder.

    This is used for a test case that is emulating a triggered
    polymorphic builder. In order to look up the builder config, the
    test case should also use chromium_tests_builder_config.properties
    to set the builder config. For recipe-side configs, instead use
    chromium_tests_builder_config.databases to create set a database
    that contains the necessary builder specs.
    """
    properties = properties_pb.InputProperties()
    target_builder_id = properties.target_builder_id
    target_builder_id.project = project
    target_builder_id.bucket = bucket
    target_builder_id.builder = builder
    properties.target_builder_group = builder_group

    return self.m.properties(**{
        '$build/chromium_polymorphic': properties,
    })
