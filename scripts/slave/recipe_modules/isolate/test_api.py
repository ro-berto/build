# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_test_api

class IsolateTestApi(recipe_test_api.RecipeTestApi):
  def output_json(self, targets):
    """Deterministically synthesize json.output test data for the given
    targets."""
    # Hash the target's name to get a bogus but deterministic value.
    return self.m.json.output(dict(
        (target, '[dummy hash for %s]' % target) for target in targets))
