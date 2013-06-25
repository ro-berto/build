# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class ChromiumApi(recipe_api.RecipeApi):
  def get_config_defaults(self, _config_name):
    return {
      'HOST_PLATFORM': self.m.platform.name,
      'HOST_ARCH': self.m.platform.arch,
      'HOST_BITS': self.m.platform.bits,
      'BUILD_CONFIG': self.m.properties.get('build_config', 'Release')
    }

  def compile(self, targets=None):
    """Return a compile.py invocation."""
    targets = targets or self.c.compile_py.default_targets.as_jsonish()
    assert isinstance(targets, (list, tuple))

    args = [
      'python', self.m.path.build('scripts', 'slave', 'compile.py'),
      '--target', self.c.BUILD_CONFIG,
      '--build-dir', self.m.path.checkout(self.c.build_dir)]
    if self.c.compile_py.build_tool:
      args += ['--build-tool', self.c.compile_py.build_tool]
    if self.c.compile_py.compiler:
      args += ['--compiler', self.c.compile_py.compiler]
    args.append('--')
    args.extend(targets)
    return self.m.step('compile', args)

  def runtests(self, test, args=None, xvfb=False, name=None, **kwargs):
    """Return a runtest.py invocation."""
    args = args or []
    assert isinstance(args, list)

    python_arg = []
    t_name, ext = self.m.path.splitext(self.m.path.basename(test))
    if ext == '.py':
      python_arg = ['--run-python-script']
    elif self.m.platform.is_win and ext == '':
      test += '.exe'

    test_args = [test] + args

    return self.m.step(name or t_name, [
      'python', self.m.path.build('scripts', 'slave', 'runtest.py'),
      '--target', self.c.BUILD_CONFIG,
      '--build-dir', self.m.path.checkout(self.c.build_dir),
      ('--xvfb' if xvfb else '--no-xvfb')]
      + self.m.json.property_args()
      + python_arg
      + test_args,
      **kwargs
    )

  def runhooks(self):
    """Run the build-configuration hooks for chromium."""
    return self.m.step(
      'gclient runhooks',
      [self.m.path.depot_tools('gclient', wrapper=True), 'runhooks'],
      env=self.c.gyp_env.as_jsonish(),
    )

