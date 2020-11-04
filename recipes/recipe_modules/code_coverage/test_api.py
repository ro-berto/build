# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from PB.recipe_modules.build.code_coverage import properties


class CodeCoverageTestApi(recipe_test_api.RecipeTestApi):

  def __call__(self,
               gs_bucket=None,
               use_clang_coverage=False,
               use_java_coverage=False,
               use_javascript_coverage=False,
               coverage_test_types=None,
               coverage_exclude_sources=None):
    return self.m.properties(
        **{
            '$build/code_coverage':
                properties.InputProperties(
                    gs_bucket=gs_bucket,
                    use_clang_coverage=use_clang_coverage,
                    use_java_coverage=use_java_coverage,
                    use_javascript_coverage=use_javascript_coverage,
                    coverage_test_types=coverage_test_types,
                    coverage_exclude_sources=coverage_exclude_sources,
                ),
        })
