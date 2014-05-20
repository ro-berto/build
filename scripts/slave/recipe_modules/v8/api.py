# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave.recipe_modules.v8 import builders


# With more than 23 letters, labels are to big for buildbot's popup boxes.
MAX_LABEL_SIZE = 23


# TODO(machenbach): This is copied from gclient's config.py and should be
# unified somehow.
def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


class V8Api(recipe_api.RecipeApi):
  BUILDERS = builders.BUILDERS

  def checkout(self, **kwargs):
    if self.m.tryserver.is_tryserver:
      yield self.m.gclient.checkout(
          revert=True, can_fail_build=False, abort_on_failure=False, **kwargs)
      for step in self.m.step_history.values():
        if step.retcode != 0:
          # TODO(phajdan.jr): Remove the workaround, http://crbug.com/357767 .
          yield (
            self.m.path.rmcontents('slave build directory',
                                   self.m.path['slave_build']),
            self.m.gclient.checkout(**kwargs),
          )
          break
    else:
      yield self.m.gclient.checkout(**kwargs)

  def runhooks(self, **kwargs):
    return self.m.chromium.runhooks(**kwargs)

  def update_clang(self):
    # TODO(machenbach): Implement this for windows or unify with chromium's
    # update clang step as soon as it exists.
    return self.m.step(
        'update clang',
        [self.m.path['checkout'].join('tools', 'clang',
                                      'scripts', 'update.sh')],
        env={'LLVM_URL': ChromiumSvnSubURL(self.m.gclient.c, 'llvm-project')})

  def compile(self, **kwargs):
    return self.m.chromium.compile(**kwargs)

  def presubmit(self):
    return self.m.python(
      'Presubmit',
      self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
      ['--testname', 'presubmit'],
      cwd=self.m.path['checkout'],
    )

  def check_initializers(self):
    return self.m.step(
      'Static-Initializers',
      ['bash',
       self.m.path['checkout'].join('tools', 'check-static-initializers.sh'),
       self.m.path.join(self.m.path.basename(self.m.chromium.c.build_dir),
                        self.m.chromium.c.build_config_fs,
                        'd8')],
      cwd=self.m.path['checkout'],
    )

  def gc_mole(self):
    # TODO(machenbach): Make gcmole work with absolute paths. Currently, a
    # particular clang version is installed on one slave in '/b'.
    env = {
      'CLANG_BIN': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole', 'bin')
      ),
      'CLANG_PLUGINS': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole')
      ),
    }
    return self.m.step(
      'GCMole',
      ['lua', self.m.path.join('tools', 'gcmole', 'gcmole.lua')],
      cwd=self.m.path['checkout'],
      env=env,
    )

  def simple_leak_check(self):
    # TODO(machenbach): Add task kill step for windows.
    relative_d8_path = self.m.path.join(
        self.m.path.basename(self.m.chromium.c.build_dir),
        self.m.chromium.c.build_config_fs,
        'd8')
    return self.m.step(
      'Simple Leak Check',
      ['valgrind', '--leak-check=full', '--show-reachable=yes',
       '--num-callers=20', relative_d8_path, '-e', '"print(1+2)"'],
      cwd=self.m.path['checkout'],
    )

  def _update_test_presentation(self, results, presentation):
    if not results:
      return

    unique_results = {}
    for result in results:
      # Use test base name as UI label (without suite and directory names).
      label = result['name'].split('/')[-1]
      # Truncate the label if it is still too long.
      if len(label) > MAX_LABEL_SIZE:
        label = label[:MAX_LABEL_SIZE - 2] + '..'
      # Group tests with the same label (usually the same test that ran under
      # different configurations).
      unique_results.setdefault(label, []).append(result)

    for label in sorted(unique_results):
      lines = []
      for result in unique_results[label]:
        lines.append('Test: %s' % result['name'])
        lines.append('Flags: %s' % " ".join(result['flags']))
        lines.append('Exit code: %s' % result['exit_code'])
        lines.append('Result: %s' % result['result'])
        lines.append('Command: %s' % result['command'])
        lines.append('')
        if result['stdout']:
          lines.append('Stdout:')
          lines.extend(result['stdout'].splitlines())
          lines.append('')
        if result['stderr']:
          lines.append('Stderr:')
          lines.extend(result['stderr'].splitlines())
          lines.append('')
      presentation.logs[label] = lines

  def _runtest(self, name, test, flaky_tests=None, **kwargs):
    env = {}
    full_args = [
      '--target', self.m.chromium.c.build_config_fs,
      '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['target_arch'],
      '--testname', test['tests'],
    ]

    # Add test-specific test arguments.
    full_args += test.get('test_args', [])

    # Add builder-specific test arguments.
    full_args += self.c.testing.test_args

    if self.c.testing.SHARD_COUNT > 1:
      full_args += [
        '--shard_count=%d' % self.c.testing.SHARD_COUNT,
        '--shard_run=%d' % self.c.testing.SHARD_RUN,
      ]

    if flaky_tests:
      full_args += ['--flaky-tests', flaky_tests]

    # Arguments and environment for asan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan') == 1:
      full_args.append('--asan')
      env['ASAN_SYMBOLIZER_PATH'] = self.m.path['checkout'].join(
          'third_party', 'llvm-build', 'Release+Asserts', 'bin',
          'llvm-symbolizer')

    if self.c.testing.show_test_results:
      full_args += ['--json-test-results',
                    self.m.json.output(add_json_log=False)]
      def followup_fn(step_result):
        r = step_result.json.output
        # The output is expected to be a list of architecture dicts that
        # each contain a results list. On buildbot, there is only one
        # architecture.
        if (r and isinstance(r, list) and isinstance(r[0], dict)):
          self._update_test_presentation(r[0]['results'],
                                         step_result.presentation)

    step_test_data = lambda: self.test_api.output_json(
        self._test_data.get('test_failures', False),
        self._test_data.get('wrong_results', False))

    yield self.m.python(
      name,
      self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
      full_args,
      cwd=self.m.path['checkout'],
      env=env,
      abort_on_failure=False,
      followup_fn=followup_fn,
      step_test_data=step_test_data,
      **kwargs
    )

    if self.c.testing.show_test_results:
      # Check integrity of the last output. The json list is expected to
      # contain only one element for one (architecture, build config type)
      # pair on the buildbot.
      result = self.m.step_history.last_step().json.output
      if result and len(result) > 1:
        yield self.m.python.inline(
            name,
            r"""
            import sys
            print 'Unexpected results set present.'
            sys.exit(1)
            """)

  def runtest(self, test, **kwargs):
    # Get the flaky-step configuration default per test.
    add_flaky_step = test.get('add_flaky_step', False)

    # Overwrite the flaky-step configuration on a per builder basis as some
    # types of builders (e.g. branch, try) don't have any flaky steps.
    if self.c.testing.add_flaky_step is not None:
      add_flaky_step = self.c.testing.add_flaky_step
    if add_flaky_step:
      return [
        self._runtest(test['name'], test, flaky_tests='skip', **kwargs),
        self._runtest(
            test['name'] + ' - flaky', test, flaky_tests='run', **kwargs),
      ]
    else:
      return self._runtest(test['name'], test, **kwargs)
