# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class FilterTestApi(recipe_test_api.RecipeTestApi):
  def suppress_analyze(self, more_exclusions=None):
    """Overrides analyze step data so that all targets get compiled."""
    return self.override_step_data(
        'read filter exclusion spec',
        self.m.json.output({
            'base': {
                'exclusions': ['f.*'] + (more_exclusions or []),
            },
            'chromium': {
                'exclusions': [],
            },
        })
    )
