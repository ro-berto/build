# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from slave import recipe_api
from slave import recipe_config_types
from common.skia import builder_name_schema
from common.skia import global_constants
from . import android_flavor
from . import chromeos_flavor
from . import default_flavor
from . import nacl_flavor
from . import valgrind_flavor
from . import xsan_flavor


def is_android(builder_cfg):
  """Determine whether the given builder is an Android builder."""
  return ('Android' in builder_cfg.get('extra_config', '') or
          builder_cfg['os'] == 'Android')


def is_chromeos(builder_cfg):
  return ('CrOS' in builder_cfg.get('extra_config', '') or
          builder_cfg['os'] == 'ChromeOS')


def is_nacl(builder_cfg):
  return 'NaCl' in builder_cfg.get('target_arch', '')


def is_valgrind(builder_cfg):
  return 'Valgrind' in builder_cfg.get('extra_config', '')


def is_xsan(builder_cfg):
  return (builder_cfg.get('extra_config') == 'ASAN' or
          builder_cfg.get('extra_config') == 'TSAN')


class SkiaApi(recipe_api.RecipeApi):

  def _set_flavor(self):
    """Return a flavor utils object specific to the given builder."""
    if is_android(self.c.builder_cfg):
      self.flavor = android_flavor.AndroidFlavorUtils(self)
    elif is_chromeos(self.c.builder_cfg):
      self.flavor = chromeos_flavor.ChromeOSFlavorUtils(self)
    elif is_nacl(self.c.builder_cfg):
      self.flavor = nacl_flavor.NaClFlavorUtils(self)
    elif is_valgrind(self.c.builder_cfg):
      self.flavor = valgrind_flavor.ValgrindFlavorUtils(self)
    elif is_xsan(self.c.builder_cfg):
      self.flavor = xsan_flavor.XSanFlavorUtils(self)
    else:
      self.flavor = default_flavor.DefaultFlavorUtils(self)

  def gen_steps(self):
    """Generate all build steps."""
    # Setup
    self.failed = []
    self.set_config('skia',
                    BUILDER_NAME=self.m.properties['buildername'],
                    MASTER_NAME=self.m.properties['mastername'],
                    SLAVE_NAME=self.m.properties['slavename'])
    self._set_flavor()

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
    self.skimage_out_dir = slave_dir.join('skimage_out')
    self.local_skp_dirs = default_flavor.SKPDirs(
        str(slave_dir.join('playback')),
        self.c.BUILDER_NAME, self.m.path.sep)
    self.storage_skp_dirs = default_flavor.SKPDirs(
        'playback', self.c.BUILDER_NAME, '/')

    self.device_dirs = self.flavor.get_device_dirs()
    self._ccache = None
    self._checked_for_ccache = False

    self.common_steps()

    if self.c.do_test_steps:
      self.test_steps()

    if self.c.do_perf_steps:
      self.perf_steps()

    if self.failed:
      raise self.m.step.StepFailure('Failed build steps: %s' %
                                    ', '.join([f.name for f in self.failed]))

  def checkout_steps(self):
    """Run the steps to obtain a checkout of Skia."""
    self.m.gclient.checkout()
    self.m.tryserver.maybe_apply_issue()

  def compile_steps(self, clobber=False):
    """Run the steps to build Skia."""
    for target in self.c.build_targets:
      self.flavor.compile(target)

  def run(self, steptype, name, abort_on_failure=True,
          fail_build_on_failure=True, **kwargs):
    """Run a step. If it fails, keep going but mark the build status failed."""
    try:
      return steptype(name, **kwargs)
    except self.m.step.StepFailure as e:
      if abort_on_failure:
        raise  # pragma: no cover
      if fail_build_on_failure:
        self.failed.append(e)

  def install(self):
    """Copy the required executables and files to the device."""
    # TODO(borenet): Only copy files which have changed.
    # Resources
    self.flavor.copy_directory_to_device(self.resource_dir,
                                         self.device_dirs.resource_dir)

    # Run any device-specific installation.
    self.flavor.install()

  def common_steps(self):
    """Steps run by both Test and Perf bots."""
    self.checkout_steps()
    self.compile_steps()
    # TODO(borenet): Implement.
    #self.download_skps()
    self.install()

  @property
  def ccache(self):
    if not self._checked_for_ccache:
      self._checked_for_ccache = True
      if not self.m.platform.is_win:
        try:
          result = self.m.step(
              'has ccache?', ['which', 'ccache'],
              stdout=self.m.raw_io.output())
          ccache = result.stdout.rstrip()
          if ccache:
            self._ccache = ccache
        except self.m.step.StepFailure:
          pass
    return self._ccache

  def run_gm(self):
    """Run the Skia GM test."""
    # Setup
    self.flavor.create_clean_device_dir(self.device_dirs.gm_actual_dir)
    host_gm_actual_dir = self.m.path['slave_build'].join('gm', 'actual',
                                                         self.c.BUILDER_NAME)
    self.flavor.create_clean_host_dir(host_gm_actual_dir)

    device_gm_expectations_path = self.flavor.device_path_join(
        self.device_dirs.gm_expected_dir, self.c.BUILDER_NAME,
        global_constants.GM_EXPECTATIONS_FILENAME)
    repo_gm_expectations_path = self.m.path['checkout'].join(
        'expectations', 'gm', self.c.BUILDER_NAME,
        global_constants.GM_EXPECTATIONS_FILENAME)
    if self.m.path.exists(repo_gm_expectations_path):
      self.flavor.copy_file_to_device(repo_gm_expectations_path,
                                      device_gm_expectations_path)

    device_ignore_tests_path = self.flavor.device_path_join(
        self.device_dirs.gm_expected_dir,
        global_constants.GM_IGNORE_TESTS_FILENAME)
    repo_ignore_tests_path = self.m.path['checkout'].join(
        'expectations', 'gm', global_constants.GM_IGNORE_TESTS_FILENAME)
    if self.m.path.exists(repo_ignore_tests_path):
      self.flavor.copy_file_to_device(repo_ignore_tests_path,
                                      device_ignore_tests_path)

    # Run the test.
    output_dir = self.flavor.device_path_join(self.device_dirs.gm_actual_dir,
                                              self.c.BUILDER_NAME)
    json_summary_path = self.flavor.device_path_join(
        output_dir, global_constants.GM_ACTUAL_FILENAME)
    args = ['gm', '--verbose', '--writeChecksumBasedFilenames',
            '--mismatchPath', output_dir,
            '--missingExpectationsPath', output_dir,
            '--writeJsonSummaryPath', json_summary_path,
            '--ignoreErrorTypes',
                'IntentionallySkipped', 'MissingExpectations',
                'ExpectationsMismatch',
            '--resourcePath', self.device_dirs.resource_dir]

    if self.flavor.device_path_exists(device_gm_expectations_path):
      args.extend(['--readPath', device_gm_expectations_path])

    if self.flavor.device_path_exists(device_ignore_tests_path):
      args.extend(['--ignoreFailuresFile', device_ignore_tests_path])

    if 'Xoom' in self.c.BUILDER_NAME:
      # The Xoom's GPU will crash on some tests if we don't use this flag.
      # http://code.google.com/p/skia/issues/detail?id=1434
      args.append('--resetGpuContext')

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
    self.run(self.flavor.step, 'gm', cmd=args, abort_on_failure=False)

    # Teardown.
    self.flavor.copy_directory_to_host(output_dir,
                                       host_gm_actual_dir)

    # Compare results to expectations.
    # TODO(borenet): Display a link to the rebaseline server. See
    # LIVE_REBASELINE_SERVER_BASEURL in
    # https://skia.googlesource.com/buildbot/+/master/slave/skia_slave_scripts/compare_gms.py
    results_file = host_gm_actual_dir.join(global_constants.GM_ACTUAL_FILENAME)
    compare_script = self.m.path['checkout'].join('gm',
                                                  'display_json_results.py')
    self.run(self.m.python, 'Compare GMs', script=compare_script,
             args=[results_file], abort_on_failure=False)

    # Upload results.
    self.run(self.m.python,
             'Upload GM Results',
             script=self.resource('upload_gm_results.py'),
             args=[str(host_gm_actual_dir), self.c.BUILDER_NAME],
             cwd=self.m.path['checkout'],
             abort_on_failure=False)

  def run_dm(self):
    """Run the DM test."""
    args = [
      'dm',
      '--verbose',
      '--resourcePath', self.device_dirs.resource_dir,
    ]

    match = []
    if 'Alex' in self.c.BUILDER_NAME:
      # This machine looks to be running out of heap.
      # Running with fewer threads may help.
      args.extend(['--threads', '1'])
    if 'Android' in self.c.BUILDER_NAME:
      match.append('~giantbitmap')
    if 'Tegra' in self.c.BUILDER_NAME:
      match.append('~downsamplebitmap_text')
    if 'Xoom' in self.c.BUILDER_NAME:
      match.append('~WritePixels')  # skia:1699
    if 'SGX540' in self.c.BUILDER_NAME:
      # Nexus S and Galaxy Nexus are still crashing.
      # Maybe the GPU's the problem?
      args.append('--nogpu')

    if match:
      args.append('--match')
      args.extend(match)
    self.run(self.flavor.step, 'dm', cmd=args, abort_on_failure=False)

    # See skia:2789.
    if 'Valgrind' in self.c.BUILDER_NAME:
      abandonGpuContext = list(args)
      abandonGpuContext.append('--abandonGpuContext')
      abandonGpuContext.append('--nocpu')
      self.run(self.flavor.step, 'dm --abandonGpuContext',
               cmd=abandonGpuContext, abort_on_failure=False)

  def test_steps(self):
    """Run all Skia test executables."""
    self.run_gm()
    self.run_dm()
    # TODO(borenet): Implement these steps.
    #self.run_render_skps()
    #self.run_render_pdfs()
    #self.run_decoding_tests()

  def perf_steps(self):
    pass
    # TODO(borenet): Implement these steps.
    # Setup
    #self.pre_perf()

    # Perf tests.
    #self.run_bench()
    #self.run_nanobench()
    #self.run_bench_pictures()

    # Teardown.
    #self.post_perf()

    # Verify results.
    #self.check_for_regressions()

    # Upload results.
    #self.upload_bench_results
