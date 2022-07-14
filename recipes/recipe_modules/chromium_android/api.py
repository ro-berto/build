# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import os
from six.moves import urllib
import textwrap

from recipe_engine.engine_types import freeze
from recipe_engine import recipe_api

_RESULT_DETAILS_LINK = 'result_details (logcats, flakiness links)'


class AndroidApi(recipe_api.RecipeApi):

  def __init__(self, **kwargs):
    super(AndroidApi, self).__init__(**kwargs)
    self._devices = None
    self._file_changes_path = None

  def get_config_defaults(self):
    return {
        'REVISION': self.m.buildbucket.gitiles_commit.id,
        'CHECKOUT_PATH': self.m.path['checkout'],
    }

  @property
  def devices(self):
    assert self._devices is not None,\
        'devices is only available after device_status()'
    return self._devices

  @property
  def out_path(self):
    return self.m.path['checkout'].join('out')

  @property
  def coverage_dir(self):
    return self.out_path.join(self.c.BUILD_CONFIG, 'coverage')

  @property
  def known_devices_file(self):
    return self.m.path.join(
        self.m.path.expanduser('~'), '.android', 'known_devices.json')

  @property
  def file_changes_path(self):
    """Get or create the path to the file containing changes for this revision.

    This file will contain a dict mapping file paths to lists of changed lines
    for each file. This is used to generate incremental coverage reports.
    """
    if not self._file_changes_path:
      self._file_changes_path = (
          self.m.path.mkdtemp('coverage').join('file_changes.json'))
    return self._file_changes_path

  def configure_from_properties(self, config_name, **kwargs):
    self.set_config(config_name, **kwargs)
    self.m.chromium.set_config(config_name, optional=True, **kwargs)

  def make_zip_archive(self,
                       step_name,
                       archive_name,
                       files=None,
                       preserve_paths=True,
                       include_filters=None,
                       exclude_filters=None,
                       **kwargs):
    """Creates and stores the archive file.

    Args:
      step_name: Name of the step.
      archive_name: Name of the archive file.
      files: If specified, only include files here instead of out/<target>.
      preserve_paths: If True, files will be stored using the subdirectories
        in the archive.
      include_filters: List of globs to be included in the archive.
      exclude_filters: List of globs to be excluded from the archive.
    """
    cmd = [
        'python',
        self.repo_resource('recipes', 'android', 'archive_build.py'),
        '--target',
        self.m.chromium.c.BUILD_CONFIG,
        '--name',
        archive_name,
    ]

    # TODO(luqui): Clean up when these are covered by the external builders.
    if files:  # pragma: no cover
      cmd.extend(['--files', ','.join(files)])
    if include_filters:
      for f in include_filters:
        cmd.extend(['--include-filter', f])
    if exclude_filters:
      for f in exclude_filters:
        cmd.extend(['--exclude-filter', f])
    if not preserve_paths:  # pragma: no cover
      cmd.append('--ignore-subfolder-names')

    with self.m.build.scripts_pythonpath():
      self.m.step(step_name, cmd, infra_step=True, **kwargs)


  def init_and_sync(self,
                    gclient_config='android_bare',
                    with_branch_heads=False,
                    use_bot_update=True,
                    use_git_cache=True):
    # TODO(crbug.com/726431): Remove this once downstream bots stop using it.
    if use_git_cache:
      spec = self.m.gclient.make_config(gclient_config)
    else:
      spec = self.m.gclient.make_config(gclient_config, CACHE_DIR=None)
    spec.target_os = ['android']
    s = spec.solutions[0]
    s.name = self.c.deps_dir
    s.url = self.c.REPO_URL
    s.deps_file = self.c.deps_file
    s.custom_vars = self.c.gclient_custom_vars or {}
    s.managed = self.c.managed
    s.revision = self.c.revision
    spec.revisions = self.c.revisions

    self.m.gclient.break_locks()
    refs = self.m.properties.get('event.patchSet.ref')
    if refs:
      refs = [refs]
    if use_bot_update:
      result = self.m.bot_update.ensure_checkout(
          spec, refs=refs, with_branch_heads=with_branch_heads)
    else:
      result = self.m.gclient.checkout(spec)

    # TODO(sivachandra): Manufacture gclient spec such that it contains "src"
    # solution + repo_name solution. Then checkout will be automatically
    # correctly set by gclient.checkout
    self.m.path['checkout'] = self.m.path['start_dir'].join('src')

    self.clean_local_files()

    return result

  def clean_local_files(self):
    target = self.c.BUILD_CONFIG
    debug_info_dumps = self.m.path['checkout'].join('out', target,
                                                    'debug_info_dumps')
    test_logs = self.m.path['checkout'].join('out', target, 'test_logs')
    build_product = self.m.path['checkout'].join('out', 'build_product.zip')
    cmd = [
        'python3',
        self.resource('clean_local_files.py'),
        debug_info_dumps,
        test_logs,
        build_product,
        self.m.path['checkout'],
    ]
    self.m.step('clean local files', cmd, infra_step=True)

  def run_tree_truth(self, additional_repos=None):
    # TODO(sivachandra): The downstream ToT builder will require
    # 'Show Revisions' step.
    repos = ['src']
    if additional_repos:
      repos.extend(additional_repos)
    if self.c.REPO_NAME not in repos and self.c.REPO_NAME:
      repos.append(self.c.REPO_NAME)
    self.m.step('tree truth steps', [
        self.m.path['checkout'].join('build', 'tree_truth.sh'),
        self.m.path['checkout']
    ] + repos)

  def resource_sizes(self,
                     apk_path,
                     chartjson_file=False,
                     perf_builder_name_alias=None,
                     step_suffix=''):
    test_name = 'resource_sizes ({})'.format(self.m.path.basename(apk_path))
    resource_sizes_args = [str(apk_path)]
    if chartjson_file:
      resource_sizes_args.append('--chartjson')

    with self.handle_exit_codes():
      self.m.chromium.runtest(
          self.c.resource_sizes,
          resource_sizes_args,
          name=test_name + step_suffix,
          perf_dashboard_id=test_name,
          point_id=None,
          test_type=test_name,
          annotate=self.m.chromium.get_annotate_by_test_name(test_name),
          results_url='https://chromeperf.appspot.com',
          perf_builder_name_alias=(perf_builder_name_alias or
                                   self.m.buildbucket.builder_name),
          chartjson_file=chartjson_file)

  def supersize_archive(self, apk_path, size_path, step_suffix=''):
    """Creates a .size file for the given .apk or .minimal.apks."""
    step_name = 'supersize archive ({}){}'.format(
        self.m.path.basename(apk_path), step_suffix)
    update_path = self.m.path['checkout'].join('tools', 'clang', 'scripts',
                                               'update.py')
    supersize_path = self.m.path['checkout'].join('tools', 'binary_size',
                                                  'supersize')
    with self.m.context(env=self.m.chromium.get_env()):
      self.m.step('download objdump', cmd=['python3', update_path,
                                           '--package=objdump'])
      return self.m.step(
          step_name,
          [supersize_path, 'archive', size_path, '-f', apk_path, '-v'])

  def upload_apks_for_bisect(self, update_properties, bucket, path):
    """Uploads android apks for functional bisects."""
    archive_name = 'build_product.zip'
    zipfile = self.m.path['checkout'].join('out', archive_name)
    with self.m.context(cwd=self.m.path['checkout']):
      self.make_zip_archive(
          'package_apks_for_bisect',
          archive_name,
          files=['apks'],
          preserve_paths=False,
      )
    # Get the commit postion for the revision to be used in archive name,
    # if not found use the git hash.
    try:
      _, rev = self.m.commit_position.parse(
          update_properties.get('got_revision_cp'))
    except ValueError:  # pragma: no cover
      rev = update_properties.get('got_revision')

    self.m.gsutil.upload(
        name='upload_apks_for_bisect',
        source=zipfile,
        bucket=bucket,
        dest=path % rev)

  def upload_build(self, bucket, path):
    archive_name = 'build_product.zip'

    zipfile = self.m.path['checkout'].join('out', archive_name)

    with self.m.context(cwd=self.m.path['checkout']):
      self.make_zip_archive(
          'zip_build_product',
          archive_name,
          preserve_paths=True,
          exclude_filters=[
              "obj/*",
              "gen/*",  # Default toolchain's obj/ and gen/
              "*/obj/*",
              "*/gen/*",  # Secondary toolchains' obj/ and gen/
              "*/thinlto-cache/*",  # ThinLTO cache directory
              "*.stamp",
              "*.d",  # Files used only for incremental builds
              "*.ninja",
              ".ninja_*",  # Build files, .ninja_log, .ninja_deps
          ])

    self.m.gsutil.upload(
        name='upload_build_product', source=zipfile, bucket=bucket, dest=path)

  def download_build(self, bucket, path, extract_path=None, globs=None):
    zipfile = self.m.path['checkout'].join('out', 'build_product.zip')
    self.m.gsutil.download(
        name='download_build_product', bucket=bucket, source=path, dest=zipfile)
    extract_path = extract_path or self.m.path['checkout']
    globs = globs or []
    with self.m.context(cwd=extract_path):
      self.m.step(
          'unzip_build_product',
          ['unzip', '-o', zipfile] + globs,
          infra_step=True,
      )

  def use_devil_adb(self):
    # TODO(crbug.com/1067294): Remove this after resolving.
    devil_path = self.m.path['checkout'].join('third_party', 'catapult',
                                              'devil')
    cmd = ['python3', self.resource('initialize_devil.py'), devil_path]
    self.m.step('initialize devil', cmd)
    self.m.adb.set_adb_path(
        devil_path.join('bin', 'deps', 'linux2', 'x86_64', 'bin', 'adb'))

  def create_adb_symlink(self):
    # Creates a sym link to the adb executable in the home dir
    cmd = [
        'python',
        self.m.path['checkout'].join('build', 'symlink.py'),
        '-f',
        self.m.adb.adb_path(),
        os.path.join('~', 'adb'),
    ]
    self.m.step('create adb symlink', cmd, infra_step=True)

  def spawn_logcat_monitor(self):
    with self.m.context(env=self.m.chromium.get_env()):
      self.m.step(
          'spawn_logcat_monitor',
          [
              'python',
              self.repo_resource('recipes', 'daemonizer.py'),
              '--',
              self.c.cr_build_android.join('adb_logcat_monitor.py'),
              self.m.chromium.c.build_dir.join('logcat'),
              self.m.adb.adb_path(),
          ],
          infra_step=True,
      )

  def spawn_device_monitor(self):
    device_monitor_script = self.m.path['checkout'].join(
        'third_party', 'catapult', 'devil', 'devil', 'android', 'tools',
        'device_monitor.py')
    self.m.step(
        'spawn_device_monitor',
        [
            'python',
            self.repo_resource('recipes', 'daemonizer.py'),
            '--action',
            'restart',
            '--pid-file-path',
            '/tmp/device_monitor.pid',
            '--',
            device_monitor_script,
            '--adb-path',
            self.m.adb.adb_path(),
            '--denylist-file',
            self.denylist_file,
        ],
        infra_step=True,
    )

  def shutdown_device_monitor(self):
    self.m.step(
        'shutdown_device_monitor',
        [
            'python',
            self.repo_resource('recipes', 'daemonizer.py'),
            '--action',
            'stop',
            '--pid-file-path',
            '/tmp/device_monitor.pid',
        ],
        infra_step=True,
    )

  def authorize_adb_devices(self):
    with self.m.context(env=self.m.chromium.get_env()):
      return self.m.step(
          'authorize_adb_devices',
          [
              'python',
              self.repo_resource('recipes', 'android',
                                 'authorize_adb_devices.py'),
              '--verbose',
              '--adb-path',
              self.m.adb.adb_path(),
          ],
          infra_step=True,
      )

  @property
  def denylist_file(self):
    return self.out_path.join('bad_devices.json')

  def non_denylisted_devices(self):
    if not self.m.path.exists(self.denylist_file):
      return self.devices
    step_result = self.m.json.read('read_denylist_file', self.denylist_file)
    denylisted_devices = step_result.json.output
    return [s for s in self.devices if s not in denylisted_devices]

  def device_status_check(self):
    self.device_recovery()
    return self.device_status()

  def host_info(self, args=None, **kwargs):
    args = args or []
    results = None
    try:
      with self.handle_exit_codes():
        if self.known_devices_file:
          known_devices_arg = ['--known-devices-file', self.known_devices_file]
          args.extend(['--args', self.m.json.input(known_devices_arg)])
        args.extend(['run', '--output', self.m.json.output()])
        with self.m.context(env=self.m.chromium.get_env()):
          results = self.m.step(
              'Host Info',
              [
                  self.m.path['checkout'].join('testing', 'scripts',
                                               'host_info.py')
              ] + args,
              infra_step=True,
              step_test_data=lambda: self.m.json.test_api.output({
                  'valid': True,
                  'failures': [],
                  '_host_info': {
                      'os_system':
                          'os_system',
                      'os_release':
                          'os_release',
                      'processor':
                          'processor',
                      'num_cpus':
                          'num_cpus',
                      'free_disk_space':
                          'free_disk_space',
                      'python_version':
                          'python_version',
                      'python_path':
                          'python_path',
                      'devices': [{
                          "usb_status": True,
                          "denylisted": None,
                          "ro.build.fingerprint": "fingerprint",
                          "battery": {
                              "status": "5",
                              "scale": "100",
                              "temperature": "240",
                              "level": "100",
                              "technology": "Li-ion",
                              "AC powered": "false",
                              "health": "2",
                              "voltage": "4302",
                              "Wireless powered": "false",
                              "USB powered": "true",
                              "Max charging current": "500000",
                              "present": "true"
                          },
                          "adb_status": "device",
                          "imei_slice": "",
                          "ro.build.product": "bullhead",
                          "ro.build.id": "MDB08Q",
                          "serial": "00d0d567893340f4",
                          "wifi_ip": ""
                      }]
                  }
              }),
              **kwargs)
      return results
    except self.m.step.InfraFailure as f:
      for failure in f.result.json.output.get('failures', []):
        f.result.presentation.logs[failure] = [failure]
      f.result.presentation.status = self.m.step.EXCEPTION

  def device_recovery(self, **kwargs):
    cmd = [
        'vpython',
        self.m.path['checkout'].join('third_party', 'catapult', 'devil',
                                     'devil', 'android', 'tools',
                                     'device_recovery.py'),
        '--denylist-file',
        self.denylist_file,
        '--known-devices-file',
        self.known_devices_file,
        '--adb-path',
        self.m.adb.adb_path(),
        '-v',
    ]
    with self.m.context(env=self.m.chromium.get_env()):
      self.m.step('device_recovery', cmd, infra_step=True, **kwargs)

  def device_status(self, **kwargs):
    buildbot_file = '/home/chrome-bot/.adb_device_info'
    args = [
        '--json-output',
        self.m.json.output(),
        '--denylist-file',
        self.denylist_file,
        '--known-devices-file',
        self.known_devices_file,
        '--buildbot-path',
        buildbot_file,
        '--adb-path',
        self.m.adb.adb_path(),
        '-v',
        '--overwrite-known-devices-files',
    ]
    try:
      with self.m.context(env=self.m.chromium.get_env()):
        result = self.m.step(
            'device_status',
            [
                self.m.path['checkout'].join('third_party', 'catapult', 'devil',
                                             'devil', 'android', 'tools',
                                             'device_status.py')
            ] + args,
            step_test_data=lambda: self.m.json.test_api.output([{
                "battery": {
                    "status": "5",
                    "scale": "100",
                    "temperature": "249",
                    "level": "100",
                    "AC powered": "false",
                    "health": "2",
                    "voltage": "4286",
                    "Wireless powered": "false",
                    "USB powered": "true",
                    "technology": "Li-ion",
                    "present": "true"
                },
                "wifi_ip":
                    "",
                "imei_slice":
                    "Unknown",
                "ro.build.id":
                    "LRX21O",
                "ro.build.product":
                    "product_name",
                "build_detail":
                    "google/razor/flo:5.0/LRX21O/1570415:userdebug/dev-keys",
                "serial":
                    "07a00ca4",
                "adb_status":
                    "device",
                "denylisted":
                    False,
                "usb_status":
                    True,
            }, {
                "adb_status": "offline",
                "denylisted": True,
                "serial": "03e0363a003c6ad4",
                "usb_status": False,
            }, {
                "adb_status": "unauthorized",
                "denylisted": True,
                "serial": "03e0363a003c6ad5",
                "usb_status": True,
            }, {
                "adb_status": "device",
                "denylisted": True,
                "serial": "03e0363a003c6ad6",
                "usb_status": True,
            }]),
            infra_step=True,
            **kwargs)
      self._devices = []
      offline_device_index = 1
      for d in result.json.output:
        try:
          if not d['usb_status']:
            key = '%s: missing' % d['serial']
          elif d['adb_status'] != 'device':
            key = '%s: adb status %s' % (d['serial'], d['adb_status'])
          elif d['denylisted']:
            key = '%s: denylisted' % d['serial']
          else:
            key = '%s %s %s' % (d['ro.build.product'], d['ro.build.id'],
                                d['serial'])
            self._devices.append(d['serial'])
        except KeyError:
          key = 'unknown device %d' % offline_device_index
          offline_device_index += 1
        result.presentation.logs[key] = self.m.json.dumps(
            d, indent=2).splitlines()
      result.presentation.step_text = 'Online devices: %s' % len(self._devices)
      return result
    except self.m.step.InfraFailure as f:
      params = [
          ('summary',
           ('Device Offline on %s %s' %
            (self.m.builder_group.for_current, self.m.properties['bot_id']))),
          ('comment', ('Buildbot: %s\n(Please do not change any labels)' %
                       self.m.buildbucket.builder_name)),
          ('labels', 'Restrict-View-Google,OS-Android,Infra,Infra-Labs'),
      ]
      link = ('https://code.google.com/p/chromium/issues/entry?%s' %
              urllib.parse.urlencode(params))
      f.result.presentation.links.update({'report a bug': link})
      raise

  def provision_devices(self,
                        skip_wipe=False,
                        disable_location=False,
                        reboot_timeout=None,
                        emulators=False,
                        **kwargs):
    if self.c and self.c.use_devil_provision:
      provision_path = self.m.path['checkout'].join('third_party', 'catapult',
                                                    'devil', 'devil', 'android',
                                                    'tools',
                                                    'provision_devices.py')
    else:
      provision_path = self.m.path['checkout'].join('build', 'android',
                                                    'provision_devices.py')
    cmd = [
        'python',
        provision_path,
        '--adb-path',
        self.m.adb.adb_path(),
        '--denylist-file',
        self.denylist_file,
        '--output-device-denylist',
        self.m.json.output(add_json_log=False),
        '-t',
        self.m.chromium.c.BUILD_CONFIG,
        '-v',
    ]
    if skip_wipe:
      cmd.append('--skip-wipe')
    if disable_location:
      cmd.append('--disable-location')
    if reboot_timeout is not None:
      assert isinstance(reboot_timeout, int)
      assert reboot_timeout > 0
      cmd.extend(['--reboot-timeout', reboot_timeout])
    if self.c and self.c.remove_system_packages:
      cmd.append('--remove-system-packages')
      cmd.extend(self.c.remove_system_packages)
    if self.c and self.c.chrome_specific_wipe:
      cmd.append('--chrome-specific-wipe')
    if emulators:
      cmd.append('--emulators')
    with self.m.context(env=self.m.chromium.get_env()):
      with self.handle_exit_codes():
        return self.m.step('provision_devices', cmd, infra_step=True, **kwargs)

  def apk_path(self, apk):
    return self.m.chromium.output_dir.join('apks', apk) if apk else None

  def adb_install_apk(self,
                      apk,
                      allow_downgrade=False,
                      keep_data=False,
                      devices=None):
    install_cmd = [
        self.m.path['checkout'].join('build', 'android', 'adb_install_apk.py'),
        apk,
        '-v',
        '--denylist-file',
        self.denylist_file,
    ]
    if int(self.m.chromium.get_version().get('MAJOR', 0)) > 50:
      install_cmd += ['--adb-path', self.m.adb.adb_path()]
    if devices and isinstance(devices, list):
      for d in devices:
        install_cmd += ['-d', d]
    if allow_downgrade:
      install_cmd.append('--downgrade')
    if keep_data:
      install_cmd.append('--keep_data')
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      install_cmd.append('--release')
    with self.m.context(env=self.m.chromium.get_env()):
      return self.m.step(
          'install ' + self.m.path.basename(apk), install_cmd, infra_step=True)

  def monkey_test(self, **kwargs):
    args = [
        'monkey',
        '-v',
        '--browser=%s' % self.c.channel,
        '--event-count=50000',
        '--denylist-file',
        self.denylist_file,
    ]
    with self.m.context(env={'BUILDTYPE': self.c.BUILD_CONFIG}):
      return self.test_runner('Monkey Test', args, **kwargs)

  def run_telemetry_browser_test(self, test_name, browser='android-chromium'):
    """Run a telemetry browser test."""
    try:
      cmd = [
          'python',
          self.m.path['checkout'].join('chrome', 'test', 'android',
                                       'telemetry_tests',
                                       'run_chrome_browser_tests.py'),
          '--browser=%s' % browser,
          '--write-abbreviated-json-results-to',
          self.m.json.output(),
          test_name,
      ]
      self.m.step(
          name='Run telemetry browser_test %s' % test_name,
          cmd=cmd,
          step_test_data=lambda: self.m.json.test_api.output(
              {'successes': ['passed_test1']}))
    finally:
      test_failures = self.m.step.active_result.json.output.get('failures', [])
      self.m.step.active_result.presentation.step_text += (
          self.m.presentation_utils.format_step_text(
              [['failures:', test_failures]]))

  def create_result_details(self, step_name, json_results_file):
    try:
      cmd = [
          'python',
          self.m.path['checkout'].join('build', 'android', 'pylib', 'results',
                                       'presentation',
                                       'test_results_presentation.py'),
          '--json-file',
          json_results_file,
          '--test-name',
          step_name,
          '--builder-name',
          self.m.buildbucket.builder_name,
          '--build-number',
          self.m.buildbucket.build.number,
          '--cs-base-url',
          self.c.cs_base_url,
          '--bucket',
          self.c.results_bucket,
      ]
      result_details = self.m.step(
          '%s: generate result details' % step_name,
          cmd,
          stdout=self.m.raw_io.output_text(),
          step_test_data=(lambda: self.m.raw_io.test_api.stream_output_text(
              'Result Details: https://storage.cloud.google.com/'
              'chromium-result-details')))
      # Stdout is in the format of 'Result Details: <link>'.
      lines = result_details.stdout.strip()
      prefix = 'Result Details: '
      return lines.splitlines()[0][len(prefix):] if lines.startswith(
          prefix) else ''
    except self.m.step.StepFailure:
      return ('https://storage.googleapis.com/chromium-result-details/'
              'UploadQuietFailure.txt')

  def logcat_dump(self):
    if self.c.logcat_bucket:
      log_path = self.m.chromium.output_dir.join('full_log')
      cmd = [
          'python', self.m.path['checkout'].join('build', 'android',
                                                 'adb_logcat_printer.py'),
          '--output-path', log_path,
          self.m.path['checkout'].join('out', 'logcat')
      ]
      self.m.step('logcat_dump', cmd, infra_step=True)
      args = []
      if self.m.tryserver.is_tryserver and not self.c.INTERNAL:
        args += ['-a', 'public-read']
      self.m.gsutil.upload(
          log_path,
          self.c.logcat_bucket,
          'logcat_dumps/%s/%s' %
          (self.m.buildbucket.builder_name, self.m.buildbucket.build.number),
          args=args,
          link_name='logcat dump',
          parallel_upload=True)

    else:
      cmd = [
          'python',
          self.repo_resource('recipes', 'tee.py'),
          self.m.chromium.output_dir.join('full_log'),
          '--',
          self.m.path['checkout'].join('build', 'android',
                                       'adb_logcat_printer.py'),
          self.m.path['checkout'].join('out', 'logcat'),
      ]
      self.m.step('logcat_dump', cmd, infra_step=True)

  def generate_breakpad_symbols(self, symbols_dir, binary_path,
                                root_chromium_dir):
    """Generate breakpad symbols.

    This step requires dump_syms binary to exist in the build dir.

    Args:
      symbols_dir: The directory to dump the breakpad symbols to.
      binary_path: Path to binary to generate symbols for.
      root_chromium_dir: Root Chromium directory.
    """
    build_dir = root_chromium_dir.join('out', self.m.chromium.c.BUILD_CONFIG)

    cmd = [
        'python',
        root_chromium_dir.join('components', 'crash', 'content', 'tools',
                               'generate_breakpad_symbols.py'),
        '--symbols-dir',
        symbols_dir,
        '--build-dir',
        build_dir,
        '--binary',
        binary_path,
    ]
    self.m.step(('generate breakpad symbols for %s' %
                 self.m.path.basename(binary_path)), cmd)

  def stackwalker(self, root_chromium_dir, binary_paths):
    """Runs stack walker tool to symbolize breakpad crashes.

    This step requires logcat file. The logcat monitor must have
    been run on the bot.

    Args:
      binary_paths: Paths to binaries to generate breakpad symbols.
      root_chromium_dir: Root Chromium directory.
    """
    build_dir = root_chromium_dir.join('out', self.m.chromium.c.BUILD_CONFIG)
    logcat = build_dir.join('full_log')

    dump_syms_path = build_dir.join('dump_syms')
    microdump_stackwalk_path = build_dir.join('microdump_stackwalk')
    required_binaries = binary_paths + [
        microdump_stackwalk_path, dump_syms_path
    ]
    if not all(map(self.m.path.exists, required_binaries)):
      result = self.m.step('skipping stackwalker step', [
          'echo',
          'Missing: %s' % ' '.join(
              [str(b) for b in required_binaries if not self.m.path.exists(b)])
      ])
      result.presentation.logs['info'] = [
          'This bot appears to not have some of the binaries required to run ',
          'stackwalker. No action is needed at this time; contact infra-dev@ ',
          'for any questions or issues'
      ]
      return

    temp_symbols_dir = self.m.path.mkdtemp('symbols')
    # TODO(mikecase): Only generate breakpad symbols if we
    # know there is at least one breakpad crash. This step takes
    # several minutes and we should only run it if we need to.
    for binary in binary_paths:
      self.generate_breakpad_symbols(temp_symbols_dir, binary,
                                     root_chromium_dir)
    cmd = [
        'python',
        root_chromium_dir.join('build', 'android', 'stacktrace',
                               'stackwalker.py'),
        '--stackwalker-binary-path',
        microdump_stackwalk_path,
        '--stack-trace-path',
        logcat,
        '--symbols-path',
        temp_symbols_dir,
    ]
    self.m.step('symbolized breakpad crashes', cmd)

  def stack_tool_steps(self, force_latest_version=False):
    build_dir = self.m.path['checkout'].join('out',
                                             self.m.chromium.c.BUILD_CONFIG)
    log_file = build_dir.join('full_log')

    target_arch = self.m.chromium.get_build_target_arch()

    # --output-directory hasn't always exited on these scripts, so use the
    # CHROMIUM_OUTPUT_DIR environment variable to avoid unrecognized flag
    # failures on older script versions (e.g. when doing bisects).
    # TODO(agrieve): Switch to --output-directory once we don't need bisects
    #     to be able to try revisions that happened before Feb 2016.
    env = self.m.chromium.get_env()
    env['CHROMIUM_OUTPUT_DIR'] = str(build_dir)
    with self.m.context(env=env):
      self.m.step(
          'stack_tool_with_logcat_dump', [
              self.m.path['checkout'].join('third_party', 'android_platform',
                                           'development', 'scripts', 'stack'),
              '--arch', target_arch, '--more-info', log_file
          ],
          infra_step=True)
    tombstones_cmd = [
        self.m.path['checkout'].join('build', 'android', 'tombstones.py'),
        '-a',
        '-s',
        '-w',
    ]
    if (force_latest_version or
        int(self.m.chromium.get_version().get('MAJOR', 0)) > 52):
      tombstones_cmd += ['--adb-path', self.m.adb.adb_path()]
    with self.m.context(env=env):
      self.m.step('stack_tool_for_tombstones', tombstones_cmd, infra_step=True)

  def common_tests_setup_steps(self, **provision_kwargs):
    if self.c.use_devil_adb:
      self.use_devil_adb()
    self.create_adb_symlink()
    self.spawn_logcat_monitor()
    self.spawn_device_monitor()
    self.authorize_adb_devices()
    self.device_recovery()
    self.provision_devices(**provision_kwargs)
    self.device_status()

  def common_tests_final_steps(self,
                               force_latest_version=False,
                               checkout_dir=None):
    self.shutdown_device_monitor()
    self.logcat_dump()
    self.stack_tool_steps(force_latest_version)

    if checkout_dir:
      binary_dir = self.m.chromium.output_dir.join('lib.unstripped')
      breakpad_binaries = [binary_dir.join('libchrome.so')]
      if self.m.path.exists(binary_dir.join('libwebviewchromium.so')):
        breakpad_binaries.append(binary_dir.join('libwebviewchromium.so'))
      self.stackwalker(
          root_chromium_dir=checkout_dir, binary_paths=breakpad_binaries)

  def run_bisect_script(self, extra_src='', path_to_config='', **kwargs):
    self.m.step('prepare bisect perf regression', [
        self.m.path['checkout'].join('tools',
                                     'prepare-bisect-perf-regression.py'), '-w',
        self.m.path['start_dir']
    ])

    args = []
    if extra_src:
      args = args + ['--extra_src', extra_src]
    if path_to_config:
      args = args + ['--path_to_config', path_to_config]
    self.m.step('run bisect perf regression', [
        self.m.path['checkout'].join('tools', 'run-bisect-perf-regression.py'),
        '-w', self.m.path['start_dir']
    ] + args, **kwargs)

  def run_test_suite(self,
                     suite,
                     verbose=True,
                     result_details=False,
                     store_tombstones=False,
                     name=None,
                     json_results_file=None,
                     shard_timeout=None,
                     args=None,
                     **kwargs):
    args = args or []
    args.extend(['--denylist-file', self.denylist_file])
    if verbose:
      args.append('--verbose')
    if result_details and not json_results_file:
      json_results_file = self.m.test_utils.gtest_results(add_json_log=False)
    if json_results_file:
      args.extend(['--json-results-file', json_results_file])
    if store_tombstones:
      args.append('--store-tombstones')
    # TODO(agrieve): Remove once no more tests pass shard_timeout (contained in
    #     wrapper scripts).
    if shard_timeout:
      args.extend(['-t', str(shard_timeout)])
    step_name = name or str(suite)
    try:
      with self.m.context(env=self.m.chromium.get_env()):
        self.test_runner(
            step_name, args=args, wrapper_script_suite_name=suite, **kwargs)
    finally:
      result_step = self.m.step.active_result
      if result_details:
        if (hasattr(result_step, 'test_utils') and
            hasattr(result_step.test_utils, 'gtest_results')):
          json_results = self.m.json.input(
              result_step.test_utils.gtest_results.raw)
          details_link = self.create_result_details(step_name, json_results)
          self.m.step.active_result.presentation.links[_RESULT_DETAILS_LINK] = (
              details_link)

  def run_java_unit_test_suite(self,
                               suite,
                               target_name=None,
                               verbose=True,
                               json_results_file=None,
                               suffix=None,
                               additional_args=None,
                               **kwargs):
    args = []
    if verbose:
      args.append('--verbose')
    if self.c.BUILD_CONFIG == 'Release':
      args.append('--release')
    if json_results_file:
      args.extend(['--json-results-file', json_results_file])
    if additional_args:
      args.extend(additional_args)

    with self.m.context(env=self.m.chromium.get_env()):
      return self.test_runner(
          '%s%s' % (str(suite), ' (%s)' % suffix if suffix else ''),
          args=args,
          wrapper_script_suite_name=str(target_name or suite),
          pass_adb_path=False,
          **kwargs)

  def coverage_report(self, upload=True, **kwargs):
    """Creates an EMMA HTML report and optionally uploads it to storage bucket.

    Creates an EMMA HTML report using generate_emma_html.py, and uploads the
    HTML report to the chrome-code-coverage storage bucket if |upload| is True.

    Args:
      upload: Uploads EMMA HTML report to storage bucket unless False is passed
        in.
      **kwargs: Kwargs for python and gsutil steps.

    Returns:
      step_result: The recipe result from generating the coverage report.
    """
    assert self.c.coverage or self.c.incremental_coverage, (
        'Trying to generate coverage report but coverage is not enabled')

    cmd = [
        'python',
        self.m.path['checkout'].join('build', 'android',
                                     'generate_emma_html.py'),
        '--coverage-dir',
        self.coverage_dir,
        '--metadata-dir',
        self.out_path.join(self.c.BUILD_CONFIG),
        '--cleanup',
        '--output',
        self.coverage_dir.join('coverage_html', 'index.html'),
    ]
    step_result = self.m.step(
        'Generate coverage report', cmd, infra_step=True, **kwargs)

    if upload:
      output_zip = self.coverage_dir.join('coverage_html.zip')
      self.m.zip.directory(
          step_name='Zip generated coverage report files',
          directory=self.coverage_dir.join('coverage_html'),
          output=output_zip)
      gs_dest = 'java/%s/%s/' % (self.m.buildbucket.builder_name,
                                 self.m.buildbucket.gitiles_commit.id)
      self.m.gsutil.upload(
          source=output_zip,
          bucket='chrome-code-coverage',
          dest=gs_dest,
          name='upload coverage report',
          link_name='Coverage report',
          **kwargs)

    return step_result

  def incremental_coverage_report(self):
    """Creates an incremental code coverage report.

    Generates a JSON file containing incremental coverage stats. Requires
    |file_changes_path| to contain a file with a valid JSON object.
    """
    with self.m.context(cwd=self.m.path['checkout']):
      cmd = [
          'python',
          self.m.path.join('build', 'android', 'emma_coverage_stats.py'),
          '-v',
          '--out',
          self.m.json.output(),
          '--emma-dir',
          self.coverage_dir.join('coverage_html'),
          '--lines-for-coverage',
          self.file_changes_path,
      ]
      step_result = self.m.step(
          'Incremental coverage report',
          cmd,
          step_test_data=lambda: self.m.json.test_api.output({
              'files': {
                  'sample file 1': {
                      'absolute': {
                          'covered': 70,
                          'total': 100,
                      },
                      'incremental': {
                          'covered': 30,
                          'total': 50,
                      },
                  },
                  'sample file 2': {
                      'absolute': {
                          'covered': 50,
                          'total': 100,
                      },
                      'incremental': {
                          'covered': 50,
                          'total': 50,
                      },
                  },
              },
              'patch': {
                  'incremental': {
                      'covered': 80,
                      'total': 100,
                  },
              },
          }))

    if step_result.json.output:
      covered_lines = step_result.json.output['patch']['incremental']['covered']
      total_lines = step_result.json.output['patch']['incremental']['total']
      percentage = covered_lines * 100.0 / total_lines if total_lines else 0

      step_result.presentation.properties['summary'] = (
          'Test coverage for this patch: %s/%s lines (%s%%).' % (
              covered_lines,
              total_lines,
              int(percentage),
          ))

      step_result.presentation.properties['moreInfoURL'] = self.m.url.join(
          self.m.properties['buildbotURL'],
          'builders',
          self.m.buildbucket.builder_name,
          'builds',
          str(self.m.buildbucket.build.number) or '0',
          'steps',
          'Incremental%20coverage%20report',
          'logs',
          'json.output',
      )

  def get_changed_lines_for_revision(self):
    """Saves a JSON file containing the files/lines requiring coverage analysis.

    Saves a JSON object mapping file paths to lists of changed lines to the
    coverage directory.
    """
    # Git provides this default value for the commit hash for staged files when
    # the -l option is used with git blame.
    blame_cached_revision = '0000000000000000000000000000000000000000'

    file_changes = {}
    new_files = self.staged_files_matching_filter('A')
    for new_file in new_files:
      lines = self.m.file.read_text(
          ('Finding lines changed in added file %s' % new_file),
          new_file,
          test_data='int n = 0;\nn++;\nfor (int i = 0; i < n; i++) {')
      file_changes[new_file] = range(1, len(lines.splitlines()) + 1)

    changed_files = self.staged_files_matching_filter('M')
    for changed_file in changed_files:
      with self.m.context(cwd=self.m.path['checkout']):
        blame = self.m.git(
            'blame',
            '-l',
            '-s',
            changed_file,
            stdout=self.m.raw_io.output_text(),
            name='Finding lines changed in modified file %s' % changed_file,
            step_test_data=(lambda: self.m.raw_io.test_api.stream_output_text(
                'int n = 0;\nn++;\nfor (int i = 0; i < n; i++) {')))
      blame_lines = blame.stdout.splitlines()
      file_changes[changed_file] = [
          i + 1
          for i, line in enumerate(blame_lines)
          if line.startswith(blame_cached_revision)
      ]

    self.m.file.write_text('Saving changed lines for revision.',
                           self.file_changes_path,
                           self.m.json.dumps(file_changes))

  def staged_files_matching_filter(self, diff_filter):
    """Returns list of files changed matching the provided diff-filter.

    Args:
      diff_filter: A string to be used as the diff-filter.

    Returns:
      A list of file paths (strings) matching the provided |diff-filter|.
    """
    with self.m.context(cwd=self.m.path['checkout']):
      diff = self.m.git(
          'diff',
          '--staged',
          '--name-only',
          '--diff-filter',
          diff_filter,
          stdout=self.m.raw_io.output_text(),
          name='Finding changed files matching diff filter: %s' % diff_filter,
          step_test_data=(lambda: self.m.raw_io.test_api.stream_output_text(
              'fake/file1.java\nfake/file2.java;\nfake/file3.java')))
    return diff.stdout.splitlines()

  @contextlib.contextmanager
  def handle_exit_codes(self):
    """Handles exit codes emitted by the test runner and other scripts."""
    EXIT_CODES = {
        'error': 1,
        'infra': 87,
        'warning': 88,
    }
    try:
      yield
    except self.m.step.StepFailure as f:
      if (f.result.retcode == EXIT_CODES['infra']):
        i = self.m.step.InfraFailure(f.name or f.reason, result=f.result)
        i.result.presentation.status = self.m.step.EXCEPTION
        raise i
      elif (f.result.retcode == EXIT_CODES['warning']):
        w = self.m.step.StepWarning(f.name or f.reason, result=f.result)
        w.result.presentation.status = self.m.step.WARNING
        raise w
      elif (f.result.retcode == EXIT_CODES['error']):
        f.result.presentation.status = self.m.step.FAILURE
      raise

  def test_runner(
      self,
      step_name,
      args=None,
      wrapper_script_suite_name=None,
      pass_adb_path=True,
      # TODO(crbug.com/1108016): Once resultdb is enabled globally,
      # makes resultdb as a required param.
      resultdb=None,
      **kwargs):
    """Wrapper for the python testrunner script.

    Args:
      step_name: Name of the step.
      args: Testrunner arguments.
      wrapper_script_suite_name: Name of wrapper_script_suite
      pass_adb_path: If True, pass the adb path with --adb-path.
      resultdb: None or chromium_tests.steps.ResultDB instance. If set with
        True in resultdb.enable, the test will be executed with ResultSink.
    """
    if not args:  # pragma: no cover
      args = []
    if pass_adb_path:
      args.extend(['--adb-path', self.m.adb.adb_path()])
    with self.handle_exit_codes():
      script = self.c.test_runner
      env = {}
      if wrapper_script_suite_name:
        script = self.m.chromium.output_dir.join(
            'bin', 'run_%s' % wrapper_script_suite_name)
      else:
        env['CHROMIUM_OUTPUT_DIR'] = self.m.context.env.get(
            'CHROMIUM_OUTPUT_DIR', self.m.chromium.output_dir)

      with self.m.context(env=env):
        cmd = [script] + args
        if resultdb and resultdb.enable:
          cmd = resultdb.wrap(self.m, cmd, step_name=step_name)
        return self.m.step(step_name, cmd, **kwargs)
