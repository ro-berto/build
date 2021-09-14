# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class FlakinessTestApi(recipe_test_api.RecipeTestApi):

  def __call__(self,
               identify_new_tests=False,
               build_count=100,
               historical_query_count=1000,
               current_query_count=10000,
               max_test_targets=10):
    return self.m.properties(
        **{
            '$build/flakiness': {
                'identify_new_tests': identify_new_tests,
                'build_count': build_count,
                'historical_query_count': historical_query_count,
                'current_query_count': current_query_count,
                'max_test_targets': max_test_targets,
            }
        })
