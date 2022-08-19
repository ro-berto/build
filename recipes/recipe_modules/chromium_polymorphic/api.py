# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe API for polymorphic builders.

Polymorphic builders are builders that are triggered on behalf of target
builders. The polymorphic builder will load the configuration of a
target builder (determined by properties set in the build request) and
execute operations using that configuration. Because the target builder
must be specified as part of the trigger, polymorphic builders can't be
run on a schedule/triggered via the scheduler, they must be triggered by
another builder or some service that sets the appropriate properties to
enable the polymorphic builder to load the correct configuration.

This module provides utilities for implementing both the triggerer and
the polymorphic builder:
* builders that trigger polymorphic builders:
  * get_target_properties
* Polymorphic builders:
  * target_builder_id
  * lookup_builder_config
"""

from typing import Dict, Optional, Tuple

from google.protobuf import json_format

from recipe_engine import recipe_api

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

from PB.go.chromium.org.luci.buildbucket.proto \
    import builder_common as builder_common_pb
from PB.go.chromium.org.luci.buildbucket.proto \
    import builds_service as builds_service_pb


class ChromiumPolymorphicApi(recipe_api.RecipeApi):

  def __init__(self, properties, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._target_builder_id = None
    self._target_builder_group = None
    if properties.HasField('target_builder_id'):
      self._target_builder_id = properties.target_builder_id
      self._target_builder_group = properties.target_builder_group

  def get_target_properties(
      self,
      target_builder_id: builder_common_pb.BuilderID,
      search_step_name: Optional[str] = None,
  ) -> Dict[str, object]:
    """Get properties for triggering a polymorphic builder.

    Args:
      target_builder_id - The Buildbucket ID of the target builder to
        trigger the polymorphic builder for.
      search_step_name - An optional step name to be used when searching
        for the most recent build of the target builder. The default
        step name of buildbucket.search will be used by default.

    Returns:
      A dict of properties to include when triggering the builder
      identified by target_builder_id. The triggered builder can
      retrieve the target_builder_id using the target_builder_id method.
      Any properties consumed by the bootstrapper to bootstrap the
      target builder will be set as well. Additional properties may be
      set, but the triggered builder should not rely on them except via
      lookup_builder.
    """
    # Get most recent build for builder from buildbucket
    build = self.m.buildbucket.search(
        builds_service_pb.BuildPredicate(builder=target_builder_id),
        limit=1,
        fields=['input.properties'],
        step_name=search_step_name)[0]

    build_props = build.input.properties

    module_props = {
        'target_builder_id': json_format.MessageToDict(target_builder_id),
    }
    # To facilitate looking up the builder config until all builder configs are
    # migrated src-side
    if 'builder_group' in build_props:
      module_props['target_builder_group'] = build_props['builder_group']

    target_props = {
        '$build/chromium_polymorphic': module_props,
    }

    # Enable the bootstrapper to load the properties for the target builder
    if '$bootstrap/properties' in build_props:
      target_props['$bootstrap/properties'] = (
          build_props['$bootstrap/properties'])

    return target_props

  @property
  def target_builder_id(self) -> builder_common_pb.BuilderID:
    """The builder ID of the target builder (in a polymoprhic builder).
    """
    assert self._target_builder_id, (
        'This property should only be accessed by polymorphic builders, '
        'which should be triggered by a builder using properties returned from '
        'get_target_properties(...)')
    return self._target_builder_id

  def lookup_builder_config(self
                           ) -> Tuple[chromium.BuilderId, ctbc.BuilderConfig]:
    """Look up the target builder's config.

    This is called by a polymorphic builder to get the builder config
    for the target builder. In order for a polymorphic builder to
    support targeting builders whose builder configs are located
    source-side and those whose builder configs are located recipe-side,
    the information necessary to lookup the target builder in the
    recipe-side static maps is included as part of the trigger. This
    looks up the builder using the key provided in the trigger.

    This also manages tester vs builder configuration: polymorphic
    builders will often need to replicate some of the behavior of
    builders and a tester, so the configuration returned when targeting
    a tester will actually be one for its parent with the target tester
    being in scope for testing. The polymorphic builder will need to
    avoid triggering the tester since that will fail or produce
    unexpected results.

    Returns:
      * The chromium BuilderId identifying the builder in source side
        specs and MB configs.
      * The builder config for the target builder.
    """
    target_builder_bb_id = self.target_builder_id
    target_builder_id = chromium.BuilderId.create_for_group(
        self._target_builder_group, target_builder_bb_id.builder)
    _, builder_config = (
        self.m.chromium_tests_builder_config.lookup_builder(target_builder_id))
    # If the target builder is not a tester, return the builder config as-is
    target_builder_spec = builder_config.builder_db[target_builder_id]
    if target_builder_spec.parent_buildername is None:
      return target_builder_id, builder_config

    # If the target builder is a tester, return a config where the target builder
    # is in scope for testing but the parent's builder spec is used for
    # configuration
    builder_id = chromium.BuilderId.create_for_group(
        target_builder_spec.parent_builder_group or target_builder_id.group,
        target_builder_spec.parent_buildername)
    return builder_id, ctbc.BuilderConfig.create(
        builder_config.builder_db,
        builder_ids=[builder_id],
        builder_ids_in_scope_for_testing=[target_builder_id],
        include_all_triggered_testers=False,
        step_api=self.m.step,
    )
