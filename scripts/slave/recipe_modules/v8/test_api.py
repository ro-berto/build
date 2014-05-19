# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

from slave import recipe_test_api
from slave.recipe_modules.v8 import builders

class V8TestApi(recipe_test_api.RecipeTestApi):
  BUILDERS = builders.BUILDERS

  def output_json(self, has_failures=False, wrong_results=False):
    if not has_failures:
      return self.m.json.output([{
        "arch": "theArch",
        "mode": "theMode",
        "results": [],
      }])
    if wrong_results:
      return self.m.json.output([{
        "arch": "theArch1",
        "mode": "theMode1",
        "results": [],
      },
      {
        "arch": "theArch2",
        "mode": "theMode2",
        "results": [],
      }])
    return self.m.json.output([{
      "arch": "theArch",
      "mode": "theMode",
      "results": [{
        "flags": ["--opt42"],
        "result": "FAIL",
        "stdout": "Some output.",
        "stderr": "Some errput.",
        "name": "suite-name/dir/test-name",
        "command": "out/theMode/d8 --opt42 test/suite-name/dir/test-name.js",
        "exit_code": 1,
      }],
    }])

  @recipe_test_api.mod_test_data
  @staticmethod
  def test_failures(has_failures):
    return has_failures

  @recipe_test_api.mod_test_data
  @staticmethod
  def wrong_results(wrong_results):
    return wrong_results

  def __call__(self, test_failures=False, wrong_results=False):
    return (self.test_failures(test_failures) +
            self.wrong_results(wrong_results))
