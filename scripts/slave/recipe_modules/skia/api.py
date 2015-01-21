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

import re


TEST_ACTUAL_SKP_VERSION = '43'
TEST_EXPECTED_SKP_VERSION = '42'


def is_android(builder_cfg):
  """Determine whether the given builder is an Android builder."""
  return ('Android' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'Android')


def is_chromeos(builder_cfg):
  return ('CrOS' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'ChromeOS')


def is_nacl(builder_cfg):
  return 'NaCl' in builder_cfg.get('target_arch', '')


def is_valgrind(builder_cfg):
  return 'Valgrind' in builder_cfg.get('extra_config', '')


def is_xsan(builder_cfg):
  return (builder_cfg.get('extra_config') == 'ASAN' or
          builder_cfg.get('extra_config') == 'TSAN' or
          builder_cfg.get('extra_config') == 'UBSAN')


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

    # self.got_revision will be set in checkout_steps.
    self.got_revision = None

    # Set some important paths.
    slave_dir = self.m.path['slave_build']
    self.skia_dir = slave_dir.join('skia')
    self.perf_data_dir = None
    if self.c.role == builder_name_schema.BUILDER_ROLE_PERF:
      self.perf_data_dir = slave_dir.join('perfdata', self.c.BUILDER_NAME,
                                          'data')
    self.resource_dir = self.skia_dir.join('resources')
    self.images_dir = slave_dir.join('images')
    self.local_skp_dirs = default_flavor.SKPDirs(
        str(slave_dir.join('playback')),
        self.c.BUILDER_NAME, self.m.path.sep)
    self.storage_skp_dirs = default_flavor.SKPDirs(
        'playback', self.c.BUILDER_NAME, '/')

    self.device_dirs = None
    self._ccache = None
    self._checked_for_ccache = False
    self._already_ran = {}

    self.common_steps()

    if self.c.do_test_steps:
      self.test_steps()

    if self.c.do_perf_steps:
      self.perf_steps()

    if self.c.do_test_steps or self.c.do_perf_steps:
      self.cleanup_steps()

    if self.failed:
      raise self.m.step.StepFailure('Failed build steps: %s' %
                                    ', '.join([f.name for f in self.failed]))

  def _run_once(self, fn, *args, **kwargs):
    if not fn.__name__ in self._already_ran:
      self._already_ran[fn.__name__] = True
      fn(*args, **kwargs)

  def checkout_steps(self):
    """Run the steps to obtain a checkout of Skia."""
    # Initial cleanup.
    if self.m.path.exists(self.skia_dir):
      if 'Win' in self.c.BUILDER_NAME:
        git = 'git.bat'
      else:
        git = 'git'
      self.run(self.m.step, 'git fetch', cmd=[git, 'fetch'], cwd=self.skia_dir)
      target_rev = self.m.properties.get('revision')
      if target_rev:
        self.run(self.m.step, 'git reset',
                 cmd=[git, 'reset', '--hard', target_rev],
                 cwd=self.skia_dir)
      self.run(self.m.step, 'git clean', cmd=[git, 'clean', '-d', '-f'],
               cwd=self.skia_dir)

    # Run 'gclient sync'.
    gclient_cfg = self.m.gclient.make_config()
    skia = gclient_cfg.solutions.add()
    skia.name = 'skia'
    skia.url = global_constants.SKIA_REPO
    gclient_cfg.got_revision_mapping['skia'] = 'got_revision'
    target_os = []
    if is_android(self.c.builder_cfg):
      target_os.append('android')
    if is_chromeos(self.c.builder_cfg):
      target_os.append('chromeos')
    gclient_cfg.target_os = target_os
    update_step = self.m.gclient.checkout(gclient_config=gclient_cfg)

    self.got_revision = update_step.presentation.properties['got_revision']
    self.m.tryserver.maybe_apply_issue()

  def compile_steps(self, clobber=False):
    """Run the steps to build Skia."""
    for target in self.c.build_targets:
      self.flavor.compile(target)

  def summarize_path(self, path):
    """Shorten path to a summary.
    >>> summarize_path('foo/bar/baz')
    .../bar/baz
    >>> summarize_path('foo/bar')
    foo/bar
    """
    path = str(path)
    parts = re.split('/|\\\\', path)  # Split on / or \.
    summary = ['...'] if len(parts) > 2 else []
    for part in parts[-2:]:
      if part == self.c.BUILDER_NAME:
        part = 'BUILDER'
      summary.append(part)
    return '/'.join(summary)

  def _readfile(self, filename, *args, **kwargs):
    """Convenience function for reading files."""
    return self.m.file.read('read %s' % self.summarize_path(filename),
                            filename, *args, **kwargs)

  def _writefile(self, filename, contents):
    """Convenience function for writing files."""
    return self.m.file.write('write %s' % filename, filename, contents)

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

  def download_and_copy_images(self):
    """Download test images if needed."""
    # TODO(mtklein,borenet): only copy when modified
    self.flavor.create_clean_host_dir(self.images_dir)
    self.m.gsutil.download(global_constants.GS_GM_BUCKET,
                           '/'.join(('skimage', 'input', '*')),
                           self.images_dir,
                           name='Download test images',
                           args=['-R'],
                           version='3.25')
    if str(self.images_dir) != str(self.device_dirs.images_dir):
      self.flavor.create_clean_device_dir(self.device_dirs.images_dir)
    self.flavor.copy_directory_contents_to_device(
        self.images_dir,
        self.device_dirs.images_dir)

  def download_and_copy_skps(self):
    """Download the SKPs if needed."""
    expected_skp_version = None
    actual_skp_version = None

    version_file = 'SKP_VERSION'
    expected_version_file = self.m.path['checkout'].join(version_file)
    expected_skp_version = self._readfile(expected_version_file,
                                          test_data=TEST_EXPECTED_SKP_VERSION)

    local_skp_path = self.local_skp_dirs.skp_dir()
    actual_version_file = self.m.path.join(local_skp_path, version_file)
    if self.m.path.exists(actual_version_file):
      actual_skp_version = self._readfile(actual_version_file,
                                          test_data=TEST_ACTUAL_SKP_VERSION)

    if actual_skp_version != expected_skp_version:
      self.flavor.create_clean_host_dir(local_skp_path)
      skp_dest = self.m.path.split(local_skp_path)[0]
      remote_skp_path = self.storage_skp_dirs.skp_dir(expected_skp_version)
      self.m.gsutil.download(global_constants.GS_GM_BUCKET, remote_skp_path,
                             skp_dest, args=['-R'], name='download skps',
                             version='3.25')
      self._writefile(actual_version_file, expected_skp_version)

    # Copy SKPs to device.
    if str(self.local_skp_dirs.skp_dir()) != str(self.device_dirs.skp_dir):
      self.flavor.create_clean_device_dir(self.device_dirs.skp_dir)
    self.flavor.copy_directory_contents_to_device(self.local_skp_dirs.skp_dir(),
                                                  self.device_dirs.skp_dir)

  def install(self):
    """Copy the required executables and files to the device."""
    self.device_dirs = self.flavor.get_device_dirs()

    # Run any device-specific installation.
    self.flavor.install()

    # TODO(borenet): Only copy files which have changed.
    # Resources
    self.flavor.copy_directory_contents_to_device(self.resource_dir,
                                                  self.device_dirs.resource_dir)

  def common_steps(self):
    """Steps run by both Test and Perf bots."""
    self.checkout_steps()
    self.compile_steps()

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

  def run_dm(self):
    """Run the DM test."""
    self._run_once(self.download_and_copy_skps)
    self._run_once(self.download_and_copy_images)
    # This must run before we write anything into self.device_dirs.dm_dir
    # or we may end up deleting our output on machines where they're the same.
    host_dm_dir = self.m.path['slave_build'].join('dm')
    self.flavor.create_clean_host_dir(host_dm_dir)

    args = [
      'dm',
      '--verbose',
      '--resourcePath', self.device_dirs.resource_dir,
      '--skps',         self.device_dirs.skp_dir,
      '--images',       self.device_dirs.images_dir,
      '--writePath',    self.device_dirs.dm_dir,
      '--nameByHash',
      '--properties',  'gitHash',      self.got_revision,
                       'build_number', self.m.properties['buildnumber'],
    ]

    configs = ['565', '8888', 'gpu', 'nvprmsaa4']
    # Xoom and NP are running out of RAM when we run all these modes.  skia:3255
    if ('Xoom'        not in self.c.BUILDER_NAME and
        'NexusPlayer' not in self.c.BUILDER_NAME):
      configs.extend(mode + '-8888' for mode in
                     ['serialize', 'tiles_rt', 'pipe'])
      configs.append('tiles_rt-gpu')
    if 'ANGLE' in self.c.BUILDER_NAME:
      configs.append('angle')
    args.append('--config')
    args.extend(configs)

    args.append('--key')
    args.extend(self._KeyParams())

    blacklist = []

    # This image is too large to be a texture for many GPUs.
    blacklist.extend('gpu _ PANO_20121023_214540.jpg'.split(' '))
    blacklist.extend('msaa _ PANO_20121023_214540.jpg'.split(' '))

    # Drawing SKPs or images into GPU canvases is a New Thing.
    # It seems like we're running out of RAM on some Android bots, so start off
    # with a very wide blacklist disabling all these tests on all Android bots.
    if 'Android' in self.c.BUILDER_NAME:  # skia:3255
      blacklist.extend('gpu skp _ gpu image _'.split(' '))
      blacklist.extend('msaa skp _ msaa image _'.split(' '))

    if blacklist:
      args.append('--blacklist')
      args.extend(blacklist)

    match = []
    if 'Alex' in self.c.BUILDER_NAME:  # skia:2793
      # This machine looks to be running out of heap.
      # Running with fewer threads may help.
      args.extend(['--threads', '1'])
    if 'Valgrind' in self.c.BUILDER_NAME: # skia:3021
      match.append('~Threaded')
    if 'Xoom' in self.c.BUILDER_NAME:  # skia:1699
      match.append('~WritePixels')

    # skia:3249: these images flakily don't decode on Android.
    if 'Android' in self.c.BUILDER_NAME:
      match.append('~tabl_mozilla_0')
      match.append('~desk_yahoonews_0')

    if match:
      args.append('--match')
      args.extend(match)

    # Though their GPUs are interesting, these don't test anything on
    # the CPU that other ARMv7+NEON bots don't test faster (N5).
    if ('Nexus10'  in self.c.BUILDER_NAME or
        'Nexus7'   in self.c.BUILDER_NAME or
        'GalaxyS4' in self.c.BUILDER_NAME):
      args.append('--nocpu')

    self.run(self.flavor.step, 'dm', cmd=args, abort_on_failure=False)

    # Copy images and JSON to host machine if needed.
    self.flavor.copy_directory_contents_to_host(self.device_dirs.dm_dir,
                                                host_dm_dir)
    # Upload them to Google Storage.
    self.run(self.m.python,
             'Upload DM Results',
             script=self.resource('upload_dm_results.py'),
             args=[
               host_dm_dir,
               self.got_revision,
               self.c.BUILDER_NAME,
               self.m.properties['buildnumber'],
               self.m.properties['issue'] if self.c.is_trybot else '',
               self.m.path['slave_build'].join("skia", "common", "py", "utils"),
             ],
             cwd=self.m.path['checkout'],
             abort_on_failure=False)

    # See skia:2789.
    if 'Valgrind' in self.c.BUILDER_NAME:
      abandonGpuContext = list(args)
      abandonGpuContext.append('--abandonGpuContext')
      abandonGpuContext.append('--nocpu')
      self.run(self.flavor.step, 'dm --abandonGpuContext',
               cmd=abandonGpuContext, abort_on_failure=False)

  def run_render_pdfs(self):
    """Render SKPs to PDFs."""
    self._run_once(self.download_and_copy_skps)
    args = ['render_pdfs', '--inputPaths', self.device_dirs.skp_dir]
    if ('Xoom'   in self.c.BUILDER_NAME or
        'Nexus7' in self.c.BUILDER_NAME):
      # Some SKPs run some Android bots out of memory.  See skia:3084.
      args.extend(['--match', '~desk_pokemonwiki',
                              '~tabl_mozilla',
                              '~tabl_nytimes'])
    self.run(self.flavor.step, 'render_pdfs', cmd=args, abort_on_failure=False)


  def test_steps(self):
    """Run all Skia test executables."""
    self._run_once(self.install)
    self.run_dm()
    if ('TSAN'         not in self.c.BUILDER_NAME and
        'ZeroGPUCache' not in self.c.BUILDER_NAME):
      self.run_render_pdfs()

  def perf_steps(self):
    """Run Skia benchmarks."""
    if self.c.BUILDER_NAME == (
        'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Debug-ZeroGPUCache'):
      return

    self._run_once(self.install)
    self._run_once(self.download_and_copy_skps)
    is_perf = self.c.role == builder_name_schema.BUILDER_ROLE_PERF
    if is_perf:
      self.flavor.create_clean_device_dir(self.device_dirs.perf_data_dir)

    # Run nanobench.
    args = ['nanobench', '-i', self.device_dirs.resource_dir,
            '--skps', self.device_dirs.skp_dir,
            '--scales', '1.0', '1.1']
    if 'Valgrind' in self.c.BUILDER_NAME:
      args.extend(['--loops', '1'])  # Don't care about Valgrind performance.
    if is_perf:
      git_timestamp = self.m.git.get_timestamp(test_data='1408633190')
      json_path = self.flavor.device_path_join(
          self.device_dirs.perf_data_dir,
          'nanobench_%s_%s.json' % (self.got_revision, git_timestamp))
      args.extend(['--outResultsFile', json_path,
                   '--properties',
                       'gitHash', self.got_revision,
                       'build_number', self.m.properties['buildnumber'],
                   ])
      keys_blacklist = ['configuration', 'role', 'is_trybot']
      args.append('--key')
      for k in sorted(self.c.builder_cfg.keys()):
        if not k in keys_blacklist:
          args.extend([k, self.c.builder_cfg[k]])

    match = []
    if 'Android' in self.c.BUILDER_NAME:
      # Segfaults when run as GPU bench. Very large texture?
      match.append('~blurroundrect')
      match.append('~patch_grid')  # skia:2847
      match.append('~desk_carsvg')
    if 'HD2000' in self.c.BUILDER_NAME:
      match.extend(['~gradient', '~etc1bitmap'])  # skia:2895
    if 'Nexus7' in self.c.BUILDER_NAME:
      match = ['skp']  # skia:2774
    if match:
      args.append('--match')
      args.extend(match)

    if 'GalaxyS4' in self.c.BUILDER_NAME:
      args.append('--nocpu')

    self.run(self.flavor.step, 'nanobench', cmd=args, abort_on_failure=False)

    if 'Valgrind' in self.c.BUILDER_NAME:  # see skia:2789
      abandonGpuContext = list(args)
      abandonGpuContext.extend(['--abandonGpuContext', '--nocpu'])
      self.run(self.flavor.step, 'nanobench --abandonGpuContext',
               cmd=abandonGpuContext, abort_on_failure=False)

    # Upload results.
    if is_perf:
      self.flavor.copy_directory_contents_to_host(
          self.device_dirs.perf_data_dir, self.perf_data_dir)
      gsutil_path = self.m.path['depot_tools'].join(
          'third_party', 'gsutil', 'gsutil')
      upload_args = [self.c.BUILDER_NAME, self.m.properties['buildnumber'],
                     self.perf_data_dir, self.got_revision, gsutil_path]
      if self.c.is_trybot:
        upload_args.append(self.m.properties['issue'])
      self.run(self.m.python,
               'Upload Nanobench Results',
               script=self.resource('upload_bench_results.py'),
               args=upload_args,
               cwd=self.m.path['checkout'],
               abort_on_failure=False)

  def cleanup_steps(self):
    """Run any cleanup steps."""
    self.flavor.cleanup_steps()

  def _KeyParams(self):
    """Build a unique key from the builder name (as a list).

    E.g.  arch x86 gpu GeForce320M mode MacMini4.1 os Mac10.6
    """
    # Don't bother to include role, which is always Test.
    # TryBots are uploaded elsewhere so they can use the same key.
    blacklist = ['role', 'is_trybot']

    params = builder_name_schema.DictForBuilderName(self.c.BUILDER_NAME)
    flat = []
    for k in sorted(params.keys()):
      if k not in blacklist:
        flat.append(k)
        flat.append(params[k])
    return flat
