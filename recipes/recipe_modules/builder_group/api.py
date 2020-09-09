# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Module for working with builder groups.

A builder group is a semi-arbitrary grouping. Some defaults are set
based on the builder group but otherwise there is no relationship in the
code between builders in the same group. The grouping exists as an
artifact of the buildbot CI system but is used heavily within the code
as part of the identifier for a builder. Until such time as it can be
removed, this provides an interface for determining a grouping.

Grouping can be retrieved for the following builders:
* current - The currently running builder.
* parent - The builder that triggered the currently running builder.
* target - The builder being targeted by the currently running builder.
    This is used by findit, where a single builder performs bisection
    for other builders by building using the target builder's
    configuration.
* bisect - The builder to run a bisection against.
    This is used by v8, where a single builder performs bisection
    for other builders by building using the bisect builder's
    configuration.

The interface also provides backwards compatibility for accessing the
grouping by the legacy method of accessing mastername properties. These
properties use names with non-inclusive language.
"""

from recipe_engine import recipe_api


class BuilderGroupApi(recipe_api.RecipeApi):

  @property
  def for_current(self):
    """Get the builder group for the currently running builder."""
    # TODO(https://crbug.com/1109276) Do not read the mastername property
    return (self.m.properties.get('builder_group') or
            self.m.properties.get('mastername'))

  @property
  def for_parent(self):
    """Get the builder group for the parent builder."""
    return self.m.properties.get('parent_builder_group')

  @property
  def for_target(self):
    """Get the builder group for the target builder.

    This is used by findit, which has a single builder that performs
    bisection using the configuration of another builder.
    """
    return self.m.properties.get('target_builder_group')
