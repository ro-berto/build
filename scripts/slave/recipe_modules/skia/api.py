# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import json
import os
import re
import sys

from recipe_engine import recipe_api

# TODO(luqui): Make this recipe stop depending on common so we can make it
# independent of build/.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))))
from common.skia import global_constants

from . import android_flavor
from . import appurify_flavor
from . import chromeos_flavor
from . import cmake_flavor
from . import coverage_flavor
from . import default_flavor
from . import fake_specs
from . import ios_flavor
from . import valgrind_flavor
from . import xsan_flavor


BOTO_CHROMIUM_SKIA_GM = 'chromium-skia-gm.boto'

GS_SUBDIR_TMPL_SK_IMAGE = 'skimage/v%s'
GS_SUBDIR_TMPL_SKP = 'playback_%s/skps'

TEST_EXPECTED_SKP_VERSION = '42'
TEST_EXPECTED_SK_IMAGE_VERSION = '42'

VERSION_FILE_SK_IMAGE = 'SK_IMAGE_VERSION'
VERSION_FILE_SKP = 'SKP_VERSION'


def is_android(builder_cfg):
  """Determine whether the given builder is an Android builder."""
  return ('Android' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'Android')


def is_appurify(builder_cfg):
  """Determine whether the builder is an Android bot running in Appurify."""
  return 'Appurify' in builder_cfg.get('extra_config', '')


def is_chromeos(builder_cfg):
  return ('CrOS' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'ChromeOS')


def is_cmake(builder_cfg):
  return 'CMake' in builder_cfg.get('extra_config', '')


def is_ios(builder_cfg):
  return ('iOS' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'iOS')


def is_valgrind(builder_cfg):
  return 'Valgrind' in builder_cfg.get('extra_config', '')


def is_xsan(builder_cfg):
  return (builder_cfg.get('extra_config') == 'ASAN' or
          builder_cfg.get('extra_config') == 'MSAN' or
          builder_cfg.get('extra_config') == 'TSAN')


def derive_compile_bot_name(builder_name, builder_cfg):
  if builder_cfg['role'] in ('Test', 'Perf'):
    os = builder_cfg['os']
    extra_config = builder_cfg.get('extra_config')
    if os in ('Android', 'ChromeOS'):  # pragma:nocover
      extra_config = os
      os = 'Ubuntu'
    elif os == 'iOS':  # pragma: nocover
      extra_config = os
      os = 'OSX'
    builder_name = 'Build-%s-%s-%s-%s' % (
      os,
      builder_cfg['compiler'],
      builder_cfg['arch'],
      builder_cfg['configuration']
    )
    if extra_config:
      builder_name += '-%s' % extra_config
  return builder_name


def swarm_dimensions(builder_cfg):
  """Return a dict of keys and values to be used as Swarming bot dimensions."""
  dimensions = {
    'pool': 'Skia',
  }
  dimensions['os'] = builder_cfg['os']
  if 'Win' in builder_cfg['os']:
    dimensions['os'] = 'Windows'  # pragma: no cover
  if builder_cfg['role'] in ('Test', 'Perf'):
    if builder_cfg['cpu_or_gpu'] == 'CPU':
      dimensions['gpu'] = 'none'
      # TODO(borenet): Add appropriate CPU dimension(s).
      #dimensions['cpu'] = builder_cfg['cpu_or_gpu_value']
    else:  # pragma: no cover
      dimensions['gpu'] = builder_cfg['cpu_or_gpu_value']
  else:
    dimensions['gpu'] = 'none'
  return dimensions


class SkiaApi(recipe_api.RecipeApi):

  def get_flavor(self, builder_cfg):
    """Return a flavor utils object specific to the given builder."""
    if is_appurify(builder_cfg):
      return appurify_flavor.AppurifyFlavorUtils(self)
    elif is_android(builder_cfg):
      return android_flavor.AndroidFlavorUtils(self)
    elif is_chromeos(builder_cfg):
      return chromeos_flavor.ChromeOSFlavorUtils(self)
    elif is_cmake(builder_cfg):
      return cmake_flavor.CMakeFlavorUtils(self)
    elif is_ios(builder_cfg):
      return ios_flavor.iOSFlavorUtils(self)
    elif is_valgrind(builder_cfg):
      return valgrind_flavor.ValgrindFlavorUtils(self)
    elif is_xsan(builder_cfg):
      return xsan_flavor.XSanFlavorUtils(self)
    elif builder_cfg.get('configuration') == global_constants.CONFIG_COVERAGE:
      return coverage_flavor.CoverageFlavorUtils(self)
    else:
      return default_flavor.DefaultFlavorUtils(self)

  def gsutil_env(self, boto_file):
    """Environment variables for gsutil."""
    boto_path = None
    if boto_file:
      boto_path = self.m.path.join(self.home_dir, boto_file)
    return {'AWS_CREDENTIAL_FILE': boto_path,
            'BOTO_CONFIG': boto_path}

  def gen_steps(self):
    """Generate all build steps."""
    # Setup
    self.failed = []

    self.builder_name = self.m.properties['buildername']
    self.master_name = self.m.properties['mastername']
    self.slave_name = self.m.properties['slavename']

    self.default_env = {}
    self.slave_dir = self.m.path['slave_build']
    self.skia_dir = self.slave_dir.join('skia')
    self.infrabots_dir = self.skia_dir.join('infra', 'bots')

    # Check out the Skia code.
    self.checkout_steps()

    # Obtain the spec for this builder from the Skia repo. Use it to set more
    # properties.
    fake_spec = None
    if self._test_data.enabled:
      fake_spec = fake_specs.FAKE_SPECS[self.builder_name]
    self.builder_spec = self.json_from_file(
      self.skia_dir.join('tools', 'buildbot_spec.py'), fake_spec)

    # Set some important variables.
    self.home_dir = os.path.expanduser('~')
    if self._test_data.enabled:
      self.home_dir = '[HOME]'
    self.perf_data_dir = None
    self.resource_dir = self.skia_dir.join('resources')
    self.images_dir = self.slave_dir.join('images')
    self.local_skp_dir = self.slave_dir.join('playback', 'skps')
    self.out_dir = self.m.path['checkout'].join('out', self.builder_name)
    self.tmp_dir = self.m.path['slave_build'].join('tmp')

    self.gsutil_env_chromium_skia_gm = self.gsutil_env(BOTO_CHROMIUM_SKIA_GM)
    # TODO(borenet): This works on GCE instance because we fall back on
    # service account auth. What about our local bots?
    self.gsutil_env_skia_infra = self.gsutil_env(None)

    self.device_dirs = None
    self._ccache = None
    self._checked_for_ccache = False
    self._already_ran = {}
    self.configuration = self.builder_spec['configuration']
    self.default_env.update({'SKIA_OUT': self.out_dir,
                             'BUILDTYPE': self.configuration})
    self.default_env.update(self.builder_spec['env'])
    self.build_targets = [str(t) for t in self.builder_spec['build_targets']]
    self.builder_cfg = self.builder_spec['builder_cfg']
    self.role = self.builder_cfg['role']
    self.do_test_steps = self.builder_spec['do_test_steps']
    self.do_perf_steps = self.builder_spec['do_perf_steps']
    self.is_trybot = self.builder_cfg['is_trybot']
    self.upload_dm_results = self.builder_spec['upload_dm_results']
    self.upload_perf_results = self.builder_spec['upload_perf_results']
    self.perf_data_dir = self.slave_dir.join('perfdata', self.builder_name,
                                             'data')
    self.dm_flags = self.builder_spec['dm_flags']
    self.nanobench_flags = self.builder_spec['nanobench_flags']

    self.flavor = self.get_flavor(self.builder_cfg)

    # Compile, run tests, perf, etc.
    if 'Swarming' in self.builder_name:
      # We don't have a Mac swarming bot yet. When we request a task for a bot
      # which doesn't exist, the task just hangs until it expires (hours). This
      # is tying up our buildslaves. Just skip the rest of the steps in this
      # case.
      if 'Mac' in self.builder_cfg.get('os', ''):
        return

      self.m.skia_swarming.setup(
          self.infrabots_dir.join('tools', 'luci-go'),
          swarming_rev='')

      compile_hash = self.compile_steps_swarm()

      test_task = None
      perf_task = None
      if self.do_test_steps:
        test_task = self.test_steps_trigger(compile_hash)
      if self.do_perf_steps:
        perf_task = self.perf_steps_trigger(compile_hash)
      if test_task:
        self.test_steps_collect(test_task)
      if perf_task:
        self.perf_steps_collect(perf_task)
    else:
      self.compile_steps()
      if self.do_test_steps:
        self.test_steps()
      if self.do_perf_steps:
        self.perf_steps()

    if self.do_test_steps or self.do_perf_steps:
      self.cleanup_steps()

    if self.failed:
      raise self.m.step.StepFailure('Failed build steps: %s' %
                                    ', '.join([f.name for f in self.failed]))

  def _run_once(self, fn, *args, **kwargs):
    if not fn.__name__ in self._already_ran:
      self._already_ran[fn.__name__] = True
      fn(*args, **kwargs)

  def update_repo(self, repo):
    """Update an existing repo. This is safe to call without gen_steps."""
    repo_path = self.m.path['slave_build'].join(repo.name)
    if self.m.path.exists(repo_path):
      if self.m.platform.is_win:
        git = 'git.bat'
      else:
        git = 'git'
      self.m.step('git remote set-url',
                  cmd=[git, 'remote', 'set-url', 'origin', repo.url],
                  cwd=repo_path,
                  infra_step=True)
      self.m.step('git fetch',
                  cmd=[git, 'fetch'],
                  cwd=repo_path,
                  infra_step=True)
      self.m.step('git reset',
                  cmd=[git, 'reset', '--hard', repo.revision],
                  cwd=repo_path,
                  infra_step=True)
      self.m.step('git clean',
                  cmd=[git, 'clean', '-d', '-f'],
                  cwd=repo_path,
                  infra_step=True)

  def checkout_steps(self):
    """Run the steps to obtain a checkout of Skia."""
    # Initial cleanup.
    if 'Swarming' in self.builder_name:
      gclient_cfg = self.m.gclient.make_config(CACHE_DIR=None)
    else:
      gclient_cfg = self.m.gclient.make_config()
    skia = gclient_cfg.solutions.add()
    skia.name = 'skia'
    skia.managed = False
    skia.url = global_constants.SKIA_REPO
    skia.revision = self.m.properties.get('revision') or 'origin/master'
    self.update_repo(skia)

    # Run 'gclient sync'.
    gclient_cfg.got_revision_mapping['skia'] = 'got_revision'
    gclient_cfg.target_os.add('llvm')
    update_step = self.m.gclient.checkout(gclient_config=gclient_cfg)

    self.got_revision = update_step.presentation.properties['got_revision']
    self.m.tryserver.maybe_apply_issue()

  def compile_steps(self, clobber=False):
    """Run the steps to build Skia."""
    for target in self.build_targets:
      self.flavor.compile(target)

  def compile_steps_swarm(self):
    builder_name = derive_compile_bot_name(self.builder_name,
                                           self.builder_cfg)
    # Windows bots require a toolchain.
    extra_hashes = None
    if 'Win' in builder_name:
      test_data = '''{
    "2013": "705384d88f80da637eb367e5acc6f315c0e1db2f",
    "2015": "38380d77eec9164e5818ae45e2915a6f22d60e85"
}'''
      hash_file = self.infrabots_dir.join('win_toolchain_hash.json')
      j = self._readfile(hash_file,
                         name='Read win_toolchain_hash.json',
                         test_data=test_data).rstrip()
      hashes = json.loads(j)
      extra_hashes = [hashes['2013']]

    # Isolate the inputs and trigger the task.
    isolate_path = self.infrabots_dir.join('compile_skia.isolate')
    isolate_vars = {'BUILDER_NAME': builder_name}
    dimensions = swarm_dimensions(self.builder_cfg)
    task = self.m.skia_swarming.isolate_and_trigger_task(
        isolate_path, self.infrabots_dir, 'compile_skia', isolate_vars,
        dimensions, idempotent=True, store_output=False,
        isolate_blacklist=['.git', 'out', '*.pyc'],
        extra_isolate_hashes=extra_hashes)

    # Wait for compile to finish, record the results hash.
    return self.m.skia_swarming.collect_swarming_task_isolate_hash(task)

  def _readfile(self, filename, *args, **kwargs):
    """Convenience function for reading files."""
    name = kwargs.pop('name') or 'read %s' % self.m.path.basename(filename)
    return self.m.file.read(name, filename, infra_step=True, *args, **kwargs)

  def _writefile(self, filename, contents):
    """Convenience function for writing files."""
    return self.m.file.write('write %s' % self.m.path.basename(filename),
                             filename, contents, infra_step=True)

  def run(self, steptype, name, abort_on_failure=True,
          fail_build_on_failure=True, env=None, **kwargs):
    """Run a step. If it fails, keep going but mark the build status failed."""
    env = dict(env or {})
    env.update(self.default_env)
    try:
      return steptype(name=name, env=env, **kwargs)
    except self.m.step.StepFailure as e:
      if abort_on_failure:
        raise  # pragma: no cover
      if fail_build_on_failure:
        self.failed.append(e)

  def gsutil_upload(self, name, source, bucket, dest):
    """Upload to Google Storage without using a .boto file."""
    self.run(
        self.m.gsutil.upload,
        name,
        source=source,
        bucket=bucket,
        dest=dest,
        args=['-R'],
        env=self.gsutil_env_skia_infra,
        abort_on_failure=False)

  def _download_and_copy_dir(self, version_file, gs_path_tmpl, host_path,
                             device_path, test_expected_version,
                             test_actual_version):
    # Ensure that the tmp_dir exists.
    self._run_once(self.m.file.makedirs,
                   'tmp_dir',
                   self.tmp_dir,
                   infra_step=True)

    expected_version_file = self.m.path['checkout'].join(version_file)
    expected_version = self._readfile(expected_version_file,
                                      name='Get expected %s' % version_file,
                                      test_data=test_expected_version).rstrip()

    actual_version_file = self.m.path.join(self.tmp_dir, version_file)
    try:
      actual_version = self._readfile(actual_version_file,
                                      name='Get downloaded %s' % version_file,
                                      test_data=test_actual_version).rstrip()
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
          (gs_path_tmpl % expected_version) + '/*',
          host_path,
          name='download %s' % self.m.path.basename(host_path),
          args=['-R'],
          env=self.gsutil_env_chromium_skia_gm)
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
    if 'Swarming' in self.builder_name:
      self.run(self.m.python, 'Download images',
               script=self.infrabots_dir.join('download_images.py'),
               env=self.gsutil_env_chromium_skia_gm)
    else:
      self._download_and_copy_dir(
          VERSION_FILE_SK_IMAGE,
          GS_SUBDIR_TMPL_SK_IMAGE,
          self.images_dir,
          self.device_dirs.images_dir,
          test_expected_version=TEST_EXPECTED_SK_IMAGE_VERSION,
          test_actual_version=self.m.properties.get(
              'test_downloaded_sk_image_version',
              TEST_EXPECTED_SK_IMAGE_VERSION))

  def download_and_copy_skps(self):
    """Download the SKPs if needed."""
    if 'Swarming' in self.builder_name:
      self.run(self.m.python, 'Download SKPs',
               script=self.infrabots_dir.join('download_skps.py'),
               env=self.gsutil_env_chromium_skia_gm)
    else:
      self._download_and_copy_dir(
          VERSION_FILE_SKP,
          GS_SUBDIR_TMPL_SKP,
          self.local_skp_dir,
          self.device_dirs.skp_dir,
          test_expected_version=TEST_EXPECTED_SKP_VERSION,
          test_actual_version=self.m.properties.get(
              'test_downloaded_skp_version', TEST_EXPECTED_SKP_VERSION))

  def install(self):
    """Copy the required executables and files to the device."""
    self.device_dirs = self.flavor.get_device_dirs()

    # Run any device-specific installation.
    self.flavor.install()

    # TODO(borenet): Only copy files which have changed.
    # Resources
    self.flavor.copy_directory_contents_to_device(self.resource_dir,
                                                  self.device_dirs.resource_dir)

  def ccache(self):
    if not self._checked_for_ccache:
      self._checked_for_ccache = True
      if not self.m.platform.is_win:
        result = self.run(
            self.m.python.inline,
            name='has ccache?',
            program='''import json
import subprocess
import sys

ccache = None
try:
  ccache = subprocess.check_output(['which', 'ccache']).rstrip()
except:
  pass
print json.dumps({'ccache': ccache})
''',
            stdout=self.m.json.output(),
            infra_step=True,
            abort_on_failure=False,
            fail_build_on_failure=False)
        if result and result.stdout and result.stdout.get('ccache'):
          self._ccache = result.stdout['ccache']

    return self._ccache

  def json_from_file(self, filename, test_data):
    """Execute the given script to obtain JSON data."""
    return self.m.python(
        'exec %s' % self.m.path.basename(filename),
        filename,
        args=[self.m.json.output(), self.builder_name],
        step_test_data=lambda: self.m.json.test_api.output(test_data),
        cwd=self.skia_dir,
        infra_step=True).json.output

  def test_steps_trigger(self, compile_hash):
    """Trigger DM via Swarming."""
    self._run_once(self.install)
    self._run_once(self.download_and_copy_skps)
    self._run_once(self.download_and_copy_images)

    # Swarm the tests.
    task_name = 'test_skia'
    isolate_path = self.infrabots_dir.join('%s.isolate' % task_name)
    issue = str(self.m.properties['issue']) if self.is_trybot else ''
    patchset = str(self.m.properties['patchset']) if self.is_trybot else ''
    isolate_vars = {
        'MASTER_NAME': self.master_name,
        'BUILDER_NAME': self.builder_name,
        'BUILD_NUMBER': str(self.m.properties['buildnumber']),
        'SLAVE_NAME': self.slave_name,
        'REVISION': self.got_revision,
        'ISSUE': issue,
        'PATCHSET': patchset,
    }

    dimensions = swarm_dimensions(self.builder_cfg)
    return self.m.skia_swarming.isolate_and_trigger_task(
        isolate_path, self.infrabots_dir, task_name, isolate_vars, dimensions,
        isolate_blacklist=['.git'], extra_isolate_hashes=[compile_hash])

  def test_steps_collect(self, task):
    """Collect the DM results from Swarming."""
    # Wait for tests to finish, download the results.
    self.m.file.rmtree('results_dir', task.task_output_dir, infra_step=True)
    self.m.skia_swarming.collect_swarming_task(task)

    # Upload the results.
    if self.upload_dm_results:
      host_dm_dir = self.m.path['slave_build'].join('dm')
      self.flavor.create_clean_host_dir(host_dm_dir)
      dm_src = task.task_output_dir.join('0', 'dm')
      self.m.file.rmtree('dm_dir', host_dm_dir, infra_step=True)
      self.m.file.copytree('dm_dir', dm_src, host_dm_dir, infra_step=True)

      # Upload them to Google Storage.
      self.run(
          self.m.python,
          'Upload DM Results',
          script=self.resource('upload_dm_results.py'),
          args=[
            host_dm_dir,
            self.got_revision,
            self.builder_name,
            self.m.properties['buildnumber'],
            self.m.properties['issue'] if self.is_trybot else '',
            self.m.path['slave_build'].join('skia', 'common', 'py', 'utils'),
          ],
          cwd=self.m.path['checkout'],
          env=self.gsutil_env_chromium_skia_gm,
          abort_on_failure=False,
          infra_step=True)

  def test_steps(self):
    """Run the DM test."""
    self._run_once(self.install)
    self._run_once(self.download_and_copy_skps)
    self._run_once(self.download_and_copy_images)

    use_hash_file = False
    if self.upload_dm_results:
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

          HASHES_URL = 'https://gold.skia.org/_/hashes'
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
    properties = [
      'gitHash',      self.got_revision,
      'master',       self.master_name,
      'builder',      self.builder_name,
      'build_number', self.m.properties['buildnumber'],
    ]
    if self.is_trybot:
      properties.extend([
        'issue',    self.m.properties['issue'],
        'patchset', self.m.properties['patchset'],
      ])

    args = [
      'dm',
      '--undefok',   # This helps branches that may not know new flags.
      '--resourcePath', self.device_dirs.resource_dir,
      '--skps', self.device_dirs.skp_dir,
      '--images', self.flavor.device_path_join(
          self.device_dirs.images_dir, 'dm'),
      '--nameByHash',
      '--properties'
    ] + properties

    args.append('--key')
    args.extend(self._KeyParams())
    if use_hash_file:
      args.extend(['--uninterestingHashesFile', hashes_file])
    if self.upload_dm_results:
      args.extend(['--writePath', self.device_dirs.dm_dir])

    skip_flag = None
    if self.builder_cfg.get('cpu_or_gpu') == 'CPU':
      skip_flag = '--nogpu'
    elif self.builder_cfg.get('cpu_or_gpu') == 'GPU':
      skip_flag = '--nocpu'
    if skip_flag:
      args.append(skip_flag)
    args.extend(self.dm_flags)

    self.run(self.flavor.step, 'dm', cmd=args, abort_on_failure=False,
             env=self.default_env)

    if self.upload_dm_results:
      # Copy images and JSON to host machine if needed.
      self.flavor.copy_directory_contents_to_host(self.device_dirs.dm_dir,
                                                  host_dm_dir)
      # Upload them to Google Storage.
      self.run(
          self.m.python,
          'Upload DM Results',
          script=self.resource('upload_dm_results.py'),
          args=[
              host_dm_dir,
              self.got_revision,
              self.builder_name,
              self.m.properties['buildnumber'],
              self.m.properties['issue'] if self.is_trybot else '',
              self.m.path['slave_build'].join('skia', 'common', 'py', 'utils'),
          ],
          cwd=self.m.path['checkout'],
          env=self.gsutil_env_chromium_skia_gm,
          abort_on_failure=False,
          infra_step=True)

    # See skia:2789.
    if ('Valgrind' in self.builder_name and
        self.builder_cfg.get('cpu_or_gpu') == 'GPU'):
      abandonGpuContext = list(args)
      abandonGpuContext.append('--abandonGpuContext')
      self.run(self.flavor.step, 'dm --abandonGpuContext',
               cmd=abandonGpuContext, abort_on_failure=False)
      preAbandonGpuContext = list(args)
      preAbandonGpuContext.append('--preAbandonGpuContext')
      self.run(self.flavor.step, 'dm --preAbandonGpuContext',
               cmd=preAbandonGpuContext, abort_on_failure=False,
               env=self.default_env)

  def perf_steps_trigger(self, compile_hash):
    """Trigger perf tests via Swarming."""
    self._run_once(self.install)
    self._run_once(self.download_and_copy_skps)
    self._run_once(self.download_and_copy_images)

    # Swarm the tests.
    task_name = 'perf_skia'
    isolate_path = self.infrabots_dir.join('%s.isolate' % task_name)
    issue = str(self.m.properties['issue']) if self.is_trybot else ''
    patchset = str(self.m.properties['patchset']) if self.is_trybot else ''
    isolate_vars = {
        'MASTER_NAME': self.master_name,
        'BUILDER_NAME': self.builder_name,
        'BUILD_NUMBER': str(self.m.properties['buildnumber']),
        'SLAVE_NAME': self.slave_name,
        'REVISION': self.got_revision,
        'ISSUE': issue,
        'PATCHSET': patchset,
    }
    dimensions = swarm_dimensions(self.builder_cfg)
    return self.m.skia_swarming.isolate_and_trigger_task(
        isolate_path, self.infrabots_dir, task_name, isolate_vars, dimensions,
        isolate_blacklist=['.git'], extra_isolate_hashes=[compile_hash])

  def perf_steps_collect(self, task):
    """Wait for perf steps to finish and upload results."""
    # Wait for nanobench to finish, download the results.
    self.m.file.rmtree('results_dir', task.task_output_dir, infra_step=True)
    self.m.skia_swarming.collect_swarming_task(task)

    # Upload the results.
    if self.upload_perf_results:
      git_timestamp = self.m.git.get_timestamp(test_data='1408633190',
                                               infra_step=True)
      self.m.file.rmtree('perf_dir', self.perf_data_dir, infra_step=True)
      self.m.file.makedirs('perf_dir', self.perf_data_dir, infra_step=True)
      src_results_file = task.task_output_dir.join(
          '0', 'perfdata', self.builder_name, 'data',
          'nanobench_%s.json' % self.got_revision)
      dst_results_file = self.perf_data_dir.join(
          'nanobench_%s_%s.json' % (self.got_revision, git_timestamp))
      self.m.file.copy('perf_results', src_results_file, dst_results_file,
                       infra_step=True)

      self.flavor.copy_directory_contents_to_host(
          self.device_dirs.perf_data_dir, self.perf_data_dir)
      gsutil_path = self.m.path['depot_tools'].join(
          'third_party', 'gsutil', 'gsutil')
      upload_args = [self.builder_name, self.m.properties['buildnumber'],
                     self.perf_data_dir, self.got_revision, gsutil_path]
      if self.is_trybot:
        upload_args.append(self.m.properties['issue'])
      self.run(self.m.python,
               'Upload perf results',
               script=self.resource('upload_bench_results.py'),
               args=upload_args,
               cwd=self.m.path['checkout'],
               env=self.gsutil_env_chromium_skia_gm,
               abort_on_failure=False,
               infra_step=True)

  def perf_steps(self):
    """Run Skia benchmarks."""
    if 'ZeroGPUCache' in self.builder_name:
      return

    self._run_once(self.install)
    self._run_once(self.download_and_copy_skps)
    self._run_once(self.download_and_copy_images)

    if self.upload_perf_results:
      self.flavor.create_clean_device_dir(self.device_dirs.perf_data_dir)

    # Run nanobench.
    properties = [
      '--properties',
      'gitHash',      self.got_revision,
      'build_number', self.m.properties['buildnumber'],
    ]
    if self.is_trybot:
      properties.extend([
        'issue',    self.m.properties['issue'],
        'patchset', self.m.properties['patchset'],
      ])

    target = 'nanobench'
    if 'VisualBench' in self.builder_name:
      target = 'visualbench'
    args = [
        target,
        '--undefok',   # This helps branches that may not know new flags.
        '-i',       self.device_dirs.resource_dir,
        '--skps',   self.device_dirs.skp_dir,
        '--images', self.flavor.device_path_join(
            self.device_dirs.images_dir, 'dm'),  # Using DM images for now.
    ]

    skip_flag = None
    if self.builder_cfg.get('cpu_or_gpu') == 'CPU':
      skip_flag = '--nogpu'
    elif self.builder_cfg.get('cpu_or_gpu') == 'GPU':
      skip_flag = '--nocpu'
    if skip_flag:
      args.append(skip_flag)
    args.extend(self.nanobench_flags)

    if self.upload_perf_results:
      git_timestamp = self.m.git.get_timestamp(test_data='1408633190',
                                               infra_step=True)
      json_path = self.flavor.device_path_join(
          self.device_dirs.perf_data_dir,
          'nanobench_%s_%s.json' % (self.got_revision, git_timestamp))
      args.extend(['--outResultsFile', json_path])
      args.extend(properties)

      keys_blacklist = ['configuration', 'role', 'is_trybot']
      args.append('--key')
      for k in sorted(self.builder_cfg.keys()):
        if not k in keys_blacklist:
          args.extend([k, self.builder_cfg[k]])

    self.run(self.flavor.step, target, cmd=args, abort_on_failure=False,
             env=self.default_env)

    # See skia:2789.
    if ('Valgrind' in self.builder_name and
        self.builder_cfg.get('cpu_or_gpu') == 'GPU'):
      abandonGpuContext = list(args)
      abandonGpuContext.extend(['--abandonGpuContext', '--nocpu'])
      self.run(self.flavor.step, '%s --abandonGpuContext' % target,
               cmd=abandonGpuContext, abort_on_failure=False,
               env=self.default_env)

    # Upload results.
    if self.upload_perf_results:
      self.m.file.makedirs('perf_dir', self.perf_data_dir)
      self.flavor.copy_directory_contents_to_host(
          self.device_dirs.perf_data_dir, self.perf_data_dir)
      gsutil_path = self.m.path['depot_tools'].join(
          'third_party', 'gsutil', 'gsutil')
      upload_args = [self.builder_name, self.m.properties['buildnumber'],
                     self.perf_data_dir, self.got_revision, gsutil_path]
      if self.is_trybot:
        upload_args.append(self.m.properties['issue'])
      self.run(self.m.python,
               'Upload %s Results' % target,
               script=self.resource('upload_bench_results.py'),
               args=upload_args,
               cwd=self.m.path['checkout'],
               env=self.gsutil_env_chromium_skia_gm,
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

    flat = []
    for k in sorted(self.builder_cfg.keys()):
      if k not in blacklist:
        flat.append(k)
        flat.append(self.builder_cfg[k])
    return flat
