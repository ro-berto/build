# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class V8Api(recipe_api.RecipeApi):
  def get_config_defaults(self, _config_name):
    ret = {}
    if 'target_arch' in self.m.properties:
      ret['TARGET_ARCH'] = self.m.properties['target_arch']
    if 'bits' in self.m.properties:
      ret['TARGET_BITS'] = self.m.properties['bits']
    if 'build_config' in self.m.properties:
      ret['BUILD_CONFIG'] = self.m.properties['build_config']
    return ret

  def checkout(self):
    return self.m.gclient.checkout()

  def runhooks(self, **kwargs):
    return self.m.chromium.runhooks(**kwargs)

  def compile(self):
    return self.m.chromium.compile()
