# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib

from slave import recipe_test_api

class IsolateTestApi(recipe_test_api.RecipeTestApi):
  def manifest_to_hash(self, targets):
    return self.output_json(targets)

  def output_json(self, targets):
    """Deterministically synthesize json.output test data for the given
    targets."""
    # Hash the target's name to get a bogus but deterministic value.
    return self.m.json.output(dict(
        (target, hashlib.sha1(target).hexdigest()) for target in targets))
