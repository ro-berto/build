# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from slave import recipe_api
from slave import recipe_config_types
from common.skia import builder_name_schema

import default_flavor


class SKPDirs(object):
  """Wraps up important directories for SKP-related testing."""

  def __init__(self, root_dir, builder_name, path_sep):
    self._root_dir = root_dir
    self._builder_name = builder_name
    self._path_sep = path_sep

  @property
  def root_dir(self):
    return self._root_dir

  @property
  def actual_images_dir(self):
    return self._path_sep.join((self.root_dir, 'actualImages',
                                self._builder_name))

  @property
  def actual_summaries_dir(self):
    return self._path_sep.join((self.root_dir, 'actualSummaries',
                                self._builder_name))

  @property
  def expected_summaries_dir(self):
    return self._path_sep.join((self.root_dir, 'expectedSummaries',
                                self._builder_name))

  def skp_dir(self, skp_version=None):
    root_dir = self.root_dir
    # TODO(borenet): The next two lines are commented out to avoid breaking
    # the coverage test. They will be uncommented when the code to use them is
    # added.
    #if skp_version:
    #  root_dir += '_%s' % skp_version
    return self._path_sep.join((root_dir, 'skps'))


class SkiaApi(recipe_api.RecipeApi):

  def gen_steps(self):
    """Generate all build steps."""
    # Setup
    self.set_config('skia', BUILDER_NAME=self.m.properties['buildername'])

    # Set some important paths.
    slave_dir = self.m.path['slave_build']
    skia_dir = slave_dir.join('skia')
    self.perf_data_dir = None
    if self.c.role == builder_name_schema.BUILDER_ROLE_PERF:
      self.perf_data_dir = slave_dir.join('perfdata', self.c.BUILDER_NAME,
                                          'data')
    self.resource_dir = skia_dir.join('resources')
    self.skimage_expected_dir = skia_dir.join('expectations', 'skimage')
    self.skimage_in_dir = slave_dir.join('skimage_in')
    self.skimage_out_dir = skia_dir.join('out', self.c.configuration,
                                         'skimage_out')
    self.local_skp_dirs = SKPDirs(str(slave_dir.join('playback')),
                                  self.c.BUILDER_NAME, self.m.path.sep)
    self.storage_skp_dirs = SKPDirs('playback', self.c.BUILDER_NAME, '/')

    # TODO(borenet): Switch this by builder type.
    self.flavor = default_flavor.DefaultFlavorUtils(self)
    self.device_dirs = self.flavor.get_device_dirs()

    self.common_steps()

    if self.c.do_test_steps:
      self.test_steps()

    if self.c.do_perf_steps:
      self.perf_steps()

  def checkout_steps(self):
    """Run the steps to obtain a checkout of Skia."""
    self.m.gclient.checkout()
    self.m.tryserver.maybe_apply_issue()

  def compile_steps(self, clobber=False):
    """Run the steps to build Skia."""

    # Run GYP to generate project files.
    env = dict(self.c.gyp_env.as_jsonish())
    self.m.python(name='gyp_skia', script='gyp_skia', env=env,
                  cwd=self.m.path['checkout'])

    # Compile each target.
    for target in self.c.build_targets:
      self.m.step('build %s' % target, ['make', target],
                  cwd=self.m.path['checkout'], env=env)

  def common_steps(self):
    """Steps run by both Test and Perf bots."""
    self.checkout_steps()
    self.compile_steps()

    # TODO(borenet): The following steps still need to be added:
    # DownloadSKPs
    # Install

  def run_tests(self):
    """Run the Skia unit tests.

    This code was adapted from
    https://skia.googlesource.com/buildbot.git/+/aa46f57/slave/skia_slave_scripts/run_tests.py
    """
    args = ['tests', '--verbose', '--tmpDir', self.device_dirs.tmp_dir,
            '--resourcePath', self.device_dirs.resource_dir]
    if 'Xoom' in self.c.BUILDER_NAME:
      # WritePixels fails on Xoom due to a bug which won't be fixed very soon.
      # http://code.google.com/p/skia/issues/detail?id=1699
      args.extend(['--match', '~WritePixels'])

    try:
      self.flavor.step('tests', args)
    except self.m.step.StepFailure:
      pass


  def run_gm(self):
    """Run the Skia GM test.

    This code was adapted from
    https://skia.googlesource.com/buildbot.git/+/aa46f57/slave/skia_slave_scripts/run_gm.py
    """
    output_dir = self.flavor.device_path_join(self.device_dirs.gm_actual_dir,
                                              self.c.BUILDER_NAME)
    json_summary_path = self.flavor.device_path_join(output_dir,
                                                     'actual_results.json')
    args = ['gm', '--verbose', '--writeChecksumBasedFilenames',
            '--mismatchPath', output_dir,
            '--missingExpectationsPath', output_dir,
            '--writeJsonSummaryPath', json_summary_path,
            '--ignoreErrorTypes',
                'IntentionallySkipped', 'MissingExpectations',
                'ExpectationsMismatch',
            '--resourcePath', self.device_dirs.resource_dir]

    device_gm_expectations_path = self.flavor.device_path_join(
        self.device_dirs.gm_expected_dir, 'expected-results.json')
    if self.flavor.device_path_exists(device_gm_expectations_path):
      args.extend(['--readPath', device_gm_expectations_path])

    device_ignore_failures_path = self.flavor.device_path_join(
        self.device_dirs.gm_expected_dir, 'ignored-tests.txt')
    if self.flavor.device_path_exists(device_ignore_failures_path):
      args.extend(['--ignoreFailuresFile', device_ignore_failures_path])

    if 'Xoom' in self.c.BUILDER_NAME:
      # The Xoom's GPU will crash on some tests if we don't use this flag.
      # http://code.google.com/p/skia/issues/detail?id=1434
      args.append('--resetGpuContext')

    # Exercise alternative renderModes, but not on the slowest platforms.
    # See https://code.google.com/p/skia/issues/detail?id=1641 ('Run GM tests
    # with all rendering modes enabled, SOMETIMES')
    # And not on Windows, which keeps running out of memory (sigh)
    # See https://code.google.com/p/skia/issues/detail?id=1783 ('Win7 Test bots
    # have out-of-memory issues')
    if (not 'Android' in self.c.BUILDER_NAME and
        not 'ChromeOS' in self.c.BUILDER_NAME and
        not 'Win7' in self.c.BUILDER_NAME):
      args.extend(['--deferred', '--pipe', '--replay', '--rtree', '--serialize',
                   '--tileGrid'])

    if 'Mac' in self.c.BUILDER_NAME:
      # msaa16 is flaky on Macs (driver bug?) so we skip the test for now
      args.extend(['--config', 'defaults', '~msaa16'])
    elif ('RazrI' in self.c.BUILDER_NAME or
          'Nexus10' in self.c.BUILDER_NAME or
          'Nexus4' in self.c.BUILDER_NAME):
      args.extend(['--config', 'defaults', 'msaa4'])
    elif 'ANGLE' in self.c.BUILDER_NAME:
      args.extend(['--config', 'angle'])
    elif (not 'NoGPU' in self.c.BUILDER_NAME and
          not 'ChromeOS' in self.c.BUILDER_NAME and
          not 'GalaxyNexus' in self.c.BUILDER_NAME and
          not 'IntelRhb' in self.c.BUILDER_NAME):
      args.extend(['--config', 'defaults', 'msaa16'])
    if 'Valgrind' in self.c.BUILDER_NAME:
      # Poppler has lots of memory errors. Skip PDF rasterisation so we don't
      # have to see them
      # Bug: https://code.google.com/p/skia/issues/detail?id=1806
      args.extend(['--pdfRasterizers'])
    if 'ZeroGPUCache' in self.c.BUILDER_NAME:
      args.extend(['--gpuCacheSize', '0', '0', '--config', 'gpu'])
    if self.c.BUILDER_NAME in ('Test-Win7-ShuttleA-HD2000-x86-Release',
                               'Test-Win7-ShuttleA-HD2000-x86-Release-Trybot'):
      args.extend(['--useDocumentInsteadOfDevice',
                   '--forcePerspectiveMatrix',
                   # Disabling the following tests because they crash GM in
                   # perspective mode.
                   # See https://code.google.com/p/skia/issues/detail?id=1665
                   '--match',
                   '~scaled_tilemodes',
                   '~convexpaths',
                   '~clipped-bitmap',
                   '~xfermodes3'])
    try:
      self.flavor.step('gm', args)
    except self.m.step.StepFailure:
      pass


  def test_steps(self):
    """Run all Skia test executables."""
    # DownloadSKImageFiles

    # PreRender (maybe rename to PreTest)

    # Unit tests.
    self.run_tests()

    # GM
    self.run_gm()

    # TODO(borenet): The following steps still need to be added:
    # RunDM
    # RenderSKPs
    # RenderPDFs
    # RunDecodingTests
    # PostRender (maybe rename to PostTest)
    # CompareGMs
    # CompareRenderedSKPs
    # UploadGMResults
    # UploadRenderedSKPs
    # UploadSKImageResults

  def perf_steps(self):
    return
    # TODO(borenet): The following steps still need to be added:
    # PreBench (maybe rename to PrePerf)
    # RunBench
    # RunNanobench
    # BenchPictures
    # PostBench (maybe rename to PostPerf)
    # CheckForRegressions
    # UploadBenchResults

