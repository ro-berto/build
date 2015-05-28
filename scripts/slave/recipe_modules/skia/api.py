# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import re
import os
import sys

from recipe_engine import recipe_api
from . import android_flavor
from . import chromeos_flavor
from . import default_flavor
from . import ios_flavor
from . import valgrind_flavor
from . import xsan_flavor

# TODO(luqui): Make this recipe stop depending on common so we can make it
# independent of build/.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))))
from common.skia import builder_name_schema
from common.skia import global_constants


# The gsutil recipe API uses a different gsutil version which does not work
# on our bots. Force the version using this constant.
GSUTIL_VERSION = '3.25'

TEST_EXPECTED_SKP_VERSION = '42'
TEST_EXPECTED_SKIMAGE_VERSION = '42'


def is_android(builder_cfg):
  """Determine whether the given builder is an Android builder."""
  return ('Android' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'Android')


def is_chromeos(builder_cfg):
  return ('CrOS' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'ChromeOS')


def is_ios(builder_cfg):
  return ('iOS' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'iOS')


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
    elif is_ios(self.c.builder_cfg):
      self.flavor = ios_flavor.iOSFlavorUtils(self)
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
    self.out_dir = None
    self.storage_skp_dirs = default_flavor.SKPDirs(
        'playback', self.c.BUILDER_NAME, '/')
    self.tmp_dir = self.m.path['slave_build'].join('tmp')

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
      self.run(self.m.step,
               'git fetch',
               cmd=[git, 'fetch'],
               cwd=self.skia_dir,
               infra_step=True)
      target_rev = self.m.properties.get('revision')
      if target_rev:
        self.run(self.m.step,
                 'git reset',
                 cmd=[git, 'reset', '--hard', target_rev],
                 cwd=self.skia_dir,
                 infra_step=True)
      self.run(self.m.step,
               'git clean',
               cmd=[git, 'clean', '-d', '-f'],
               cwd=self.skia_dir,
               infra_step=True)

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
    self.out_dir = self.m.path['checkout'].join('out', self.c.BUILDER_NAME)

  def compile_steps(self, clobber=False):
    """Run the steps to build Skia."""
    for target in self.c.build_targets:
      self.flavor.compile(target, env={'SKIA_OUT': self.out_dir})

  def _readfile(self, filename, *args, **kwargs):
    """Convenience function for reading files."""
    name = kwargs.pop('name') or 'read %s' % self.m.path.basename(filename)
    return self.m.file.read(name, filename, infra_step=True, *args, **kwargs)

  def _writefile(self, filename, contents):
    """Convenience function for writing files."""
    return self.m.file.write('write %s' % self.m.path.basename(filename),
                             filename, contents, infra_step=True)

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

  def _download_and_copy_dir(self, expected_version, version_file, gs_path,
                             host_path, device_path, test_actual_version):
    actual_version_file = self.m.path.join(self.tmp_dir, version_file)
    try:
      actual_version = self._readfile(actual_version_file,
                                      name='Get downloaded %s' % version_file,
                                      test_data=test_actual_version)
    except self.m.step.StepFailure:
      actual_version = -1

    # If we don't have the desired version, download it.
    if actual_version != expected_version:
      if actual_version != -1:
        self.m.file.remove('remove actual %s' % version_file,
                           actual_version_file,
                           infra_step=True)

      self.flavor.create_clean_host_dir(host_path)
      self.m.gsutil.download(
          global_constants.GS_GM_BUCKET,
          gs_path + '/*',
          host_path,
          name='download %s' % self.m.path.basename(host_path),
          args=['-R'],
          version=GSUTIL_VERSION)
      self._writefile(actual_version_file, expected_version)

    # Copy to device.
    device_version_file = self.flavor.device_path_join(
        self.device_dirs.tmp_dir, version_file)
    if str(actual_version_file) != str(device_version_file):
      try:
        device_version = self.flavor.read_file_on_device(device_version_file)
      except self.m.step.StepFailure:
        device_version = -1
      if device_version != expected_version:
        self.flavor.remove_file_on_device(device_version_file)
        self.flavor.create_clean_device_dir(device_path)
        self.flavor.copy_directory_contents_to_device(host_path, device_path)

        # Copy the new version file.
        self.flavor.copy_file_to_device(actual_version_file,
                                        device_version_file)

  def download_and_copy_images(self):
    """Download test images if needed."""
    # Ensure that the tmp_dir exists.
    self._run_once(self.m.file.makedirs,
                   'tmp_dir',
                   self.tmp_dir,
                   infra_step=True)

    # Determine which version we have and which version we want.
    timestamp_file = 'TIMESTAMP_LAST_UPLOAD_COMPLETED'
    url = '/'.join(('gs:/', global_constants.GS_GM_BUCKET, 'skimage', 'input',
                    timestamp_file))
    expected_version = self.m.gsutil.cat(
        url,
        name='cat %s' % timestamp_file,
        version=GSUTIL_VERSION,
        stdout=self.m.raw_io.output()).stdout.rstrip()

    test_data = TEST_EXPECTED_SKIMAGE_VERSION
    if self.m.properties.get('test_downloaded_skimage_version'):
      test_data = self.m.properties['test_downloaded_skimage_version']

    self._download_and_copy_dir(expected_version,
                                'SKIMAGE_VERSION',
                                '/'.join(('skimage', 'input')),
                                self.images_dir,
                                self.device_dirs.images_dir,
                                test_actual_version=test_data)

  def download_and_copy_skps(self):
    """Download the SKPs if needed."""
    # Ensure that the tmp_dir exists.
    self._run_once(self.m.file.makedirs,
                   'tmp_dir',
                   self.tmp_dir,
                   infra_step=True)

    # Determine which version we have and which version we want.
    version_file = 'SKP_VERSION'
    expected_version_file = self.m.path['checkout'].join(version_file)
    expected_version = self._readfile(expected_version_file,
                                      name='Get expected SKP_VERSION',
                                      test_data=TEST_EXPECTED_SKP_VERSION)

    test_data = TEST_EXPECTED_SKP_VERSION
    if self.m.properties.get('test_downloaded_skp_version'):
      test_data = self.m.properties['test_downloaded_skp_version']

    self._download_and_copy_dir(expected_version,
                                version_file,
                                self.storage_skp_dirs.skp_dir(expected_version),
                                self.local_skp_dirs.skp_dir(),
                                self.device_dirs.skp_dir,
                                test_actual_version=test_data)

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
              'has ccache?',
              ['which', 'ccache'],
              stdout=self.m.raw_io.output(),
              infra_step=True)
          ccache = result.stdout.rstrip()
          if ccache:
            self._ccache = ccache
        except self.m.step.StepFailure:
          pass
    return self._ccache

  def flags_from_file(self, filename):
    """Execute the given script to obtain flags to pass to a test."""
    return self.m.python(
        'exec %s' % self.m.path.basename(filename),
        filename,
        args=[self.m.json.output(), self.c.BUILDER_NAME],
        step_test_data=lambda: self.m.json.test_api.output(['--dummy-flags']),
        cwd=self.skia_dir,
        infra_step=True).json.output

  def run_dm(self):
    """Run the DM test."""
    self._run_once(self.download_and_copy_skps)
    self._run_once(self.download_and_copy_images)
    # This must run before we write anything into self.device_dirs.dm_dir
    # or we may end up deleting our output on machines where they're the same.
    host_dm_dir = self.m.path['slave_build'].join('dm')
    self.flavor.create_clean_host_dir(host_dm_dir)
    if str(host_dm_dir) != str(self.device_dirs.dm_dir):
      self.flavor.create_clean_device_dir(self.device_dirs.dm_dir)

    # Obtain the list of already-generated hashes.
    hash_filename = 'uninteresting_hashes.txt'
    host_hashes_file = self.tmp_dir.join(hash_filename)
    hashes_file = self.flavor.device_path_join(
        self.device_dirs.tmp_dir, hash_filename)
    use_hash_file = False
    self.run(
        self.m.python.inline,
        'get uninteresting hashes',
        program="""
        import contextlib
        import math
        import socket
        import sys
        import time
        import urllib2

        HASHES_URL = 'https://gold.skia.org/2/_/hashes'
        RETRIES = 5
        TIMEOUT = 60
        WAIT_BASE = 15

        socket.setdefaulttimeout(TIMEOUT)
        for retry in range(RETRIES):
          try:
            with contextlib.closing(
                urllib2.urlopen(HASHES_URL, timeout=TIMEOUT)) as w:
              hashes = w.read()
              with open(sys.argv[1], 'w') as f:
                f.write(hashes)
                break
          except:
            print 'Failed to get uninteresting hashes from %s' % HASHES_URL
            if retry == RETRIES:
              raise
            waittime = WAIT_BASE * math.pow(2, retry)
            print 'Retry in %d seconds.' % waittime
            time.sleep(waittime)
        """,
        args=[host_hashes_file],
        cwd=self.skia_dir,
        abort_on_failure=False,
        fail_build_on_failure=False,
        infra_step=True)

    if self.m.path.exists(host_hashes_file):
      self.flavor.copy_file_to_device(host_hashes_file, hashes_file)
      use_hash_file = True

    # Run DM.
    args = [
      'dm',
      '--undefok',   # This helps branches that may not know new flags.
      '--verbose',
      '--resourcePath', self.device_dirs.resource_dir,
      '--skps',         self.device_dirs.skp_dir,
      '--images',       self.device_dirs.images_dir,
      '--writePath',    self.device_dirs.dm_dir,
      '--nameByHash',
      '--properties',  'gitHash',      self.got_revision,
                       'build_number', self.m.properties['buildnumber'],
    ]
    args.append('--key')
    args.extend(self._KeyParams())
    if use_hash_file:
      args.extend(['--uninterestingHashesFile', hashes_file])

    skip_flag = None
    if self.c.builder_cfg.get('cpu_or_gpu') == 'CPU':
      skip_flag = '--nogpu'
    elif self.c.builder_cfg.get('cpu_or_gpu') == 'GPU':
      skip_flag = '--nocpu'
    if skip_flag:
      args.append(skip_flag)

    args.extend(self.flags_from_file(self.skia_dir.join('tools/dm_flags.py')))
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
             abort_on_failure=False,
             infra_step=True)

    # See skia:2789.
    if ('Valgrind' in self.c.BUILDER_NAME and
        self.c.builder_cfg.get('cpu_or_gpu') == 'GPU'):
      abandonGpuContext = list(args)
      abandonGpuContext.append('--abandonGpuContext')
      self.run(self.flavor.step, 'dm --abandonGpuContext',
               cmd=abandonGpuContext, abort_on_failure=False)
      # preAbandonGpuContext does not write out any images
      preAbandonGpuContext = list(args)
      index = 0
      for i, x in enumerate(preAbandonGpuContext):
        if isinstance(x, basestring) and x == '--writePath':
          index = i
      del preAbandonGpuContext[index:index+2]
      preAbandonGpuContext.append('--preAbandonGpuContext')
      self.run(self.flavor.step, 'dm --preAbandonGpuContext',
               cmd=preAbandonGpuContext, abort_on_failure=False)

  def test_steps(self):
    """Run all Skia test executables."""
    self._run_once(self.install)
    self.run_dm()

  def perf_steps(self):
    """Run Skia benchmarks."""
    if 'ZeroGPUCache' in self.c.BUILDER_NAME:
      return

    self._run_once(self.install)
    self._run_once(self.download_and_copy_skps)
    is_perf = self.c.role == builder_name_schema.BUILDER_ROLE_PERF
    if is_perf:
      self.flavor.create_clean_device_dir(self.device_dirs.perf_data_dir)

    # Run nanobench.
    args = [
        'nanobench',
        '--undefok',   # This helps branches that may not know new flags.
        '-i', self.device_dirs.resource_dir,
        '--skps', self.device_dirs.skp_dir
    ]

    skip_flag = None
    if self.c.builder_cfg.get('cpu_or_gpu') == 'CPU':
      skip_flag = '--nogpu'
    elif self.c.builder_cfg.get('cpu_or_gpu') == 'GPU':
      skip_flag = '--nocpu'
    if skip_flag:
      args.append(skip_flag)

    args.extend(self.flags_from_file(self.skia_dir.join(
        'tools/nanobench_flags.py')))
    if is_perf:
      git_timestamp = self.m.git.get_timestamp(test_data='1408633190',
                                               infra_step=True)
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

    self.run(self.flavor.step, 'nanobench', cmd=args, abort_on_failure=False)

    # See skia:2789.
    if ('Valgrind' in self.c.BUILDER_NAME and
        self.c.builder_cfg.get('cpu_or_gpu') == 'GPU'):
      abandonGpuContext = list(args)
      abandonGpuContext.extend(['--abandonGpuContext', '--nocpu'])
      self.run(self.flavor.step, 'nanobench --abandonGpuContext',
               cmd=abandonGpuContext, abort_on_failure=False)

    # Upload results.
    if is_perf:
      self.m.file.makedirs('perf_dir', self.perf_data_dir)
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
               abort_on_failure=False,
               infra_step=True)

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
