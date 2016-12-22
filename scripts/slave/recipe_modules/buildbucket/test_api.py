# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import recipe_test_api

class BuildbucketTestApi(recipe_test_api.RecipeTestApi):

  def simulated_buildbucket_output(self, additional_build_parameters):
    buildbucket_output = {
        'build':{
          'parameters_json': json.dumps(additional_build_parameters)
        }
    }

    return self.step_data(
        'buildbucket.get',
        stdout=self.m.raw_io.output(json.dumps(buildbucket_output)))

