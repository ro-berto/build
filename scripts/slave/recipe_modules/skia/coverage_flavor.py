# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import default_flavor
import posixpath
import ssh_devices


"""Utils for running coverage tests."""


class CoverageFlavorUtils(default_flavor.DefaultFlavorUtils):
  def compile(self, target, env=None):
    """Build the given target."""
    env = env or {}
    env['BUILDTYPE'] = self._skia_api.c.configuration
    # We have to use Clang 3.6 because earlier versions do not support the
    # compile flags we use and 3.7 and 3.8 hit asserts during compilation.
    env['CC'] = '/usr/bin/clang-3.6'
    env['CXX'] = '/usr/bin/clang-3.6'
    cmd = [self._skia_api.m.path['slave_build'].join('skia', 'tools',
                                                     'llvm_coverage_build'),
           target]
    self._skia_api.m.step('build %s' % target, cmd, env=env,
                          cwd=self._skia_api.m.path['checkout'])

  def step(self, name, cmd, env=None, **kwargs):
    """Run the given step through coverage."""
    if not env:
      env = {}
    env['SKIA_OUT'] = self._skia_api.out_dir
    results_dir = self._skia_api.out_dir.join('coverage_results')
    self.create_clean_host_dir(results_dir)
    git_timestamp = self._skia_api.m.git.get_timestamp(test_data='1408633190',
                                                       infra_step=True)
    results_file = results_dir.join('nanobench_%s_%s.json' % (
        self._skia_api.got_revision, git_timestamp))
    args = [
        'python',
        self._skia_api.m.path['slave_build'].join('skia', 'tools',
                                                  'llvm_coverage_run.py'),
    ] + cmd + [
        '--outResultsFile', results_file,
    ]
    self._skia_api.m.step(name=name, cmd=args, env=env,
                          cwd=self._skia_api.m.path['checkout'], **kwargs)
    gsutil_path = self._skia_api.m.path['depot_tools'].join(
        'third_party', 'gsutil', 'gsutil')
    upload_args = [self._skia_api.c.BUILDER_NAME,
                   self._skia_api.m.properties['buildnumber'],
                   results_dir,
                   self._skia_api.got_revision, gsutil_path]
    if self._skia_api.c.is_trybot:
      upload_args.append(self._skia_api.m.properties['issue'])
    self._skia_api.run(
        self._skia_api.m.python,
        'Upload Coverage Results',
        script=self._skia_api.resource('upload_bench_results.py'),
        args=upload_args,
        cwd=self._skia_api.m.path['checkout'],
        abort_on_failure=False,
        infra_step=True)
