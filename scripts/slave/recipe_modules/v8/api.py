# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class V8Api(recipe_api.RecipeApi):
  def _get_v8_target_architecture(self):
    """Return v8ish architecture names."""
    target_arch = self.m.properties.get('target_arch', 'intel')
    bits = self.m.properties.get('bits', None) or self.m.platform.bits

    if target_arch == 'arm':
      return 'arm'
    elif bits == 64:
      return 'x64'
    else:
      return 'ia32'

  def checkout(self):
    cfg = self.m.gclient.make_config()
    soln = cfg.solutions.add()
    soln.name = 'v8'
    soln.url = 'http://v8.googlecode.com/svn/branches/bleeding_edge'
    return self.m.gclient.checkout(cfg)

  def runhooks(self):
    gclient_env = {
      'GYP_DEFINES': 'v8_target_arch=%s' % self._get_v8_target_architecture(),
    }
    return self.m.gclient.runhooks(env=gclient_env)

  def compile(self):
    compile_tool = self.m.path.build('scripts', 'slave', 'compile.py')
    build_config = self.m.properties.get('build_config', 'Release')
    compile_args = [
      '--target', build_config,
      '--build-dir', 'v8',
      '--src-dir', 'v8',
      '--build-tool', 'make',
      'buildbot',
    ]
    if self.m.properties.get('clobber') is not None:
      compile_args.append('--clobber')
    return self.m.python('compile', compile_tool, compile_args)
