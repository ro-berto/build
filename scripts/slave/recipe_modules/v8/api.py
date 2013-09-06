# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class V8Api(recipe_api.RecipeApi):
  def get_config_defaults(self, _config_name):
    return {
      'HOST_PLATFORM': self.m.platform.name,
      'HOST_ARCH': self.m.platform.arch,
      'HOST_BITS': self.m.platform.bits,
      'TARGET_ARCH': self.m.properties.get('target_arch', 'intel'),
      'TARGET_BITS': self.m.properties.get('bits', 32),
      'BUILD_CONFIG': self.m.properties.get('build_config', 'Release')
    }

  def checkout(self):
    return self.m.gclient.checkout()

  def runhooks(self, **kwargs):
    env = kwargs.get('env', {})
    env.update(self.c.gyp_env.as_jsonish())
    kwargs['env'] = env
    return self.m.gclient.runhooks(**kwargs)

  def compile(self):
    compile_tool = self.m.path.build('scripts', 'slave', 'compile.py')
    compile_args = [
      '--target', self.c.BUILD_CONFIG,
      '--build-dir', 'v8',
      '--src-dir', 'v8',
      '--build-tool', 'make',
      'buildbot',
    ]
    if self.m.properties.get('clobber') is not None:
      compile_args.append('--clobber')
    return self.m.python('compile', compile_tool, compile_args)
