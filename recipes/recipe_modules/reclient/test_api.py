# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class ReclientTestApi(recipe_test_api.RecipeTestApi):

  def properties(self, instance='example'):
    return self.m.properties(**{
        '$build/reclient': {
            'instance': instance,
        },
    })
