# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


# TODO(machenbach): This is copied from gclient's config.py and should be
# unified somehow.
def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


class V8Api(recipe_api.RecipeApi):
  def checkout(self):
    return self.m.gclient.checkout()

  def runhooks(self, **kwargs):
    return self.m.chromium.runhooks(**kwargs)

  def update_clang(self):
    # TODO(machenbach): Implement this for windows or unify with chromium's
    # update clang step as soon as it exists.
    return self.m.step(
        'update clang',
        [self.m.path.checkout('tools', 'clang', 'scripts', 'update.sh')],
        env={'LLVM_URL': ChromiumSvnSubURL(self.m.gclient.c, 'llvm-project')})

  def compile(self):
    return self.m.chromium.compile()

  def _runtest(self, name, tests, flaky_tests=None):
    env = {}
    full_args = [
      '--target', self.m.chromium.c.build_config_fs,
      '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['target_arch'],
      '--testname', tests,
    ]
    if flaky_tests:
      full_args += ['--flaky-tests', flaky_tests]

    # Arguments and environment for asan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan') == 1:
      full_args.append('--asan')
      env['ASAN_SYMBOLIZER_PATH'] = self.m.path.checkout(
          'third_party', 'llvm-build', 'Release+Asserts', 'bin',
          'llvm-symbolizer')

    return self.m.python(
      name,
      self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
      full_args,
      cwd=self.m.path['checkout'],
      env=env
    )

  def runtest(self, test):
    if test['flaky_step']:
      return [
        self._runtest(test['name'],
                      test['tests'],
                      flaky_tests='skip'),
        self._runtest(test['name'] + ' - flaky',
                      test['tests'],
                      flaky_tests='run'),
      ]
    else:
      return self._runtest(test['name'], test['tests'])
