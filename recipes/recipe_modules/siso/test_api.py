# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class SisoTestApi(recipe_test_api.RecipeTestApi):

  def properties(self,
                 siso_version='latest',
                 project='test-rbe-project',
                 reapi_address=None,
                 reapi_instance='default_instance',
                 deps_log_bucket='siso-deps-log-experiments',
                 enable_cloud_trace=None,
                 enable_cloud_profiler=None,
                 action_salt=None):
    return self.m.properties(
        **{
            '$build/siso': {
                'siso_version': siso_version,
                'project': project,
                'reapi_address': reapi_address,
                'reapi_instance': reapi_instance,
                'deps_log_bucket': deps_log_bucket,
                'enable_cloud_trace': enable_cloud_trace,
                'enable_cloud_profiler': enable_cloud_profiler,
                'action_salt': action_salt,
            },
        })
