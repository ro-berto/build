# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class ReclientTestApi(recipe_test_api.RecipeTestApi):

  def properties(self,
                 instance='example',
                 metrics_project=None,
                 rewrapper_env=None,
                 profiler_service=None,
                 publish_trace=None,
                 cache_silo="test silo",
                 fail_early=None,
                 ensure_verified=None):
    if rewrapper_env is None:
      rewrapper_env = {}

    return self.m.properties(
        **{
            '$build/reclient': {
                'instance': instance,
                'metrics_project': metrics_project,
                'rewrapper_env': rewrapper_env,
                'profiler_service': profiler_service,
                'publish_trace': publish_trace,
                'cache_silo': cache_silo,
                'ensure_verified': ensure_verified,
                'fail_early': fail_early,
            },
        }) + self.m.buildbucket.ci_build(
            project='chromium', bucket='ci', builder='Linux reclient')
