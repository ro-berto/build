# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class ChromiumApi(recipe_api.RecipeApi):
  def get_config_defaults(self):
    return {
      'HOST_PLATFORM': self.m.platform.name,
      'HOST_ARCH': self.m.platform.arch,
      'HOST_BITS': self.m.platform.bits,

      'TARGET_PLATFORM': self.m.platform.name,
      'TARGET_ARCH': self.m.platform.arch,

      # This should probably default to the platform.bits, but right now this
      # is the more expected configuration.
      'TARGET_BITS': 32,

      'BUILD_CONFIG': self.m.properties.get('build_config', 'Release')
    }

  def compile(self, targets=None, name=None, **kwargs):
    """Return a compile.py invocation."""
    targets = targets or self.c.compile_py.default_targets.as_jsonish()
    assert isinstance(targets, (list, tuple))

    args = [
      '--target', self.c.build_config_fs,
      '--build-dir', self.m.path.checkout(self.c.build_dir),
      '--src-dir', self.m.path.checkout(),
    ]
    if self.c.compile_py.build_tool:
      args += ['--build-tool', self.c.compile_py.build_tool]
    if self.c.compile_py.compiler:
      args += ['--compiler', self.c.compile_py.compiler]
    if self.m.properties.get('clobber') is not None:
      args.append('--clobber')
    args.append('--')
    args.extend(targets)
    return self.m.python(name or 'compile',
                         self.m.path.build('scripts', 'slave', 'compile.py'),
                         args, **kwargs)

  def runtests(self, test, args=None, xvfb=False, name=None, **kwargs):
    """Return a runtest.py invocation."""
    args = args or []
    assert isinstance(args, list)

    t_name, ext = self.m.path.splitext(self.m.path.basename(test))
    if self.m.platform.is_win and ext == '':
      test += '.exe'

    full_args = [
      '--target', self.c.build_config_fs,
      '--build-dir', self.m.path.checkout(self.c.build_dir),
      ('--xvfb' if xvfb else '--no-xvfb')
    ]
    full_args += self.m.json.property_args()
    if ext == '.py':
      full_args.append('--run-python-script')
    full_args.append(test)
    full_args.extend(args)

    # By default, don't abort the recipe for a single test failure.
    kwargs.setdefault('can_fail_build', False)

    return self.m.python(
      name or t_name,
      self.m.path.build('scripts', 'slave', 'runtest.py'),
      full_args,
      **kwargs
    )

  def runhooks(self, **kwargs):
    """Run the build-configuration hooks for chromium."""
    env = kwargs.get('env', {})
    env.update(self.c.gyp_env.as_jsonish())
    kwargs['env'] = env
    return self.m.gclient.runhooks(**kwargs)

