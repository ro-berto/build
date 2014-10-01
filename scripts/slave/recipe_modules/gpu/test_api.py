# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_test_api

import common

class GpuTestApi(recipe_test_api.RecipeTestApi):
  @property
  def dummy_swarm_hashes(self):
    return dict(
      (target, '[dummy hash for %s]' % target)
        for target in common.GPU_ISOLATE_MAPPING.keys())

  @property
  def analyze_builds_everything(self):
    return self.m.json.output({
        'status': 'Found dependency',
        'targets': common.GPU_ISOLATE_MAPPING.keys(),
        'build_targets': [u'%s_run' % test
                          for test in common.GPU_ISOLATE_MAPPING.keys()]})
