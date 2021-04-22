# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             mapping, sequence)
from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc


@attrs()
class TargetConfig(object):
  """"Dynamic" configuration for a bot.

  BuildConfig provides access to information obtained from src-side files; for a
  given recipe version BuildConfig information can change on a per-src-revision
  basis. There could potentially be multiple BuildConfigs for the same build
  that contain different information (e.g. a trybot running against a change
  that modifies the src-side spec information).

  This creates a directed acyclic builder graph, with the builders
  described by the provided bot IDs as the root nodes and the builders
  they trigger as their children. Nodes keep track of whether they're
  referenced by a bot ID (and would thus be mirrored by trybots).
  """

  builder_config = attrib(ctbc.BuilderConfig)
  # The values should be a mapping from builder name to the raw test specs for
  # the builder (mapping[str, mapping[str, ...]]), but if we enforce that here,
  # then a bad spec for one builder would cause all builders that read that file
  # to fail, so we don't apply any constraints to the value here to limit the
  # blast radius of bad changes
  _source_side_specs = attrib(mapping[str, ...])
  # The elements of the values should be chromium_tests.steps.Test instances,
  # but that would cause an import cycle. It's not expected that anyone will be
  # creating TargetConfigs manually, so don't enforce the type, just trust that
  # the chromium_tests generators will return back the correct type
  _tests = attrib(mapping[chromium.BuilderId, sequence])

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)

  # TODO(https://crbug.com/1193832) Remove this once all callers are migrated to
  # use builder_config
  @cached_property
  def bot_config(self):
    return self.builder_config  # pragma: no cover

  # NOTE: All of the tests_in methods are returning mutable objects
  # (and we expect them to be mutated, e.g., to update the swarming
  # command lines to use when we determine what they are).
  def _get_tests_for(self, keys):
    tests = []
    for k in keys:
      tests.extend(self._tests[k])
    return tests

  def all_tests(self):
    """Returns all tests."""
    return self._get_tests_for(self.builder_config.all_keys)

  def tests_in_scope(self):
    """Returns all tests for the provided bot IDs."""
    return self._get_tests_for(self.builder_config.root_keys)

  def tests_on(self, builder_id):
    """Returns all tests for the specified builder."""
    return self._get_tests_for([builder_id])

  def tests_triggered_by(self, builder_id):
    """Returns all tests for builders triggered by the specified builder."""
    return self._get_tests_for(
        self.builder_config.builder_db.builder_graph[builder_id])

  def get_compile_targets(self, tests):
    compile_targets = set()

    for builder_id in self.builder_config.builder_ids:
      source_side_spec = self._source_side_specs[builder_id.group].get(
          builder_id.builder, {})
      compile_targets.update(
          source_side_spec.get('additional_compile_targets', []))

    for t in tests:
      compile_targets.update(t.compile_targets())

    return sorted(compile_targets)
