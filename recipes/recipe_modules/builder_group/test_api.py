# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


# TODO(https://crbug.com/1109276) Remove the *mastername properties, update
# docstrings
class ChromiumTestApi(recipe_test_api.RecipeTestApi):

  def for_current(self, group):
    """Set the builder group for the currently running builder.

    This also sets the legacy mastername property so existing code
    continues to work.
    """
    # TODO(https://crbug.com/1109276) Do not set the mastername property
    return self.m.properties(builder_group=group, mastername=group)

  def for_parent(self, group):
    """Set the builder group for the parent builder."""
    return self.m.properties(parent_builder_group=group)

  def for_target(self, group):
    """Set the builder group for the target builder.

    This is used by findit, which has a single builder that performs
    bisection using the configuration of another builder.
    """
    return self.m.properties(target_builder_group=group)
