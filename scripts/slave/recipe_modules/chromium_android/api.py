# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import datetime
import json
import os
import pipes
import re
import sys
import textwrap
import urllib

from recipe_engine.types import freeze
from recipe_engine import recipe_api

def _TimestampToIsoFormat(timestamp):
  return datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y%m%dT%H%M%S')


class AndroidApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(AndroidApi, self).__init__(**kwargs)
    self._devices = None
    self._file_changes_path = None

  def get_config_defaults(self):
    return {
      'REVISION': self.m.properties.get('revision', ''),
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

  def make_zip_archive(self, step_name, archive_name, files=None,
                       preserve_paths=True, filters=None, **kwargs):
    """Creates and stores the archive file.

    Args:
      step_name: Name of the step.
      archive_name: Name of the archive file.
      files: If specified, only include files here instead of out/<target>.
      filters: List of globs to be included in the archive.
      preserve_paths: If True, files will be stored using the subdolders
        in the archive.
    """
    archive_args = ['--target', self.m.chromium.c.BUILD_CONFIG,
                    '--name', archive_name]

    # TODO(luqui): Clean up when these are covered by the external builders.
    if files:              # pragma: no cover
      archive_args.extend(['--files', ','.join(files)])
    if filters:
      archive_args.extend(['--filters', ','.join(filters)])
    if not preserve_paths: # pragma: no cover
      archive_args.append('--ignore-subfolder-names')

    self.m.python(
      step_name,
      str(self.package_repo_resource(
          'scripts', 'slave', 'android', 'archive_build.py')),
      archive_args,
      infra_step=True,
      **kwargs
    )

  def init_and_sync(self, gclient_config='android_bare',
                    with_branch_heads=False, use_bot_update=True,
                    use_git_cache=True):
    # TODO(sivachandra): Move the setting of the gclient spec below to an
    # internal config extension when they are supported by the recipe system.
    if use_git_cache:
      spec = self.m.gclient.make_config(gclient_config)
    else:
      spec = self.m.gclient.make_config(gclient_config,
                                        CACHE_DIR=None)
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
      result = self.m.gclient.checkout(
          spec, with_branch_heads=with_branch_heads)

    # TODO(sivachandra): Manufacture gclient spec such that it contains "src"
    # solution + repo_name solution. Then checkout will be automatically
    # correctly set by gclient.checkout
    self.m.path['checkout'] = self.m.path['start_dir'].join('src')

    self.clean_local_files()

    return result

  def clean_local_files(self, clean_pyc_files=True):
    target = self.c.BUILD_CONFIG
    debug_info_dumps = self.m.path['checkout'].join('out',
                                                    target,
                                                    'debug_info_dumps')
    test_logs = self.m.path['checkout'].join('out', target, 'test_logs')
    build_product = self.m.path['checkout'].join('out', 'build_product.zip')
    python_inline_script = textwrap.dedent("""
        import shutil, sys, os
        shutil.rmtree(sys.argv[1], True)
        shutil.rmtree(sys.argv[2], True)
        try:
          os.remove(sys.argv[3])
        except OSError:
          pass
        """)
    if clean_pyc_files:
      python_inline_script += textwrap.dedent("""\
          for base, _dirs, files in os.walk(sys.argv[4]):
            for f in files:
              if f.endswith('.pyc'):
                os.remove(os.path.join(base, f))
      """)

    self.m.python.inline(
      'clean local files',
      python_inline_script,
      args=[debug_info_dumps, test_logs, build_product,
            self.m.path['checkout']],
      infra_step=True,
    )

  def run_tree_truth(self, additional_repos=None):
    # TODO(sivachandra): The downstream ToT builder will require
    # 'Show Revisions' step.
    repos = ['src']
    if additional_repos:
      repos.extend(additional_repos)
    if self.c.REPO_NAME not in repos and self.c.REPO_NAME:
      repos.append(self.c.REPO_NAME)
    # TODO(sivachandra): Disable subannottations after cleaning up
    # tree_truth.sh.
    self.m.step('tree truth steps',
                [self.m.path['checkout'].join('build', 'tree_truth.sh'),
                self.m.path['checkout']] + repos,
                allow_subannotations=False)

  def git_number(self, **kwargs):
    return self.m.step(
        'git_number',
        [self.m.depot_tools.package_repo_resource('git_number.py')],
        stdout = self.m.raw_io.output_text(),
        step_test_data=(
          lambda:
            self.m.raw_io.test_api.stream_output('3000\n')
        ),
        cwd=self.m.path['checkout'],
        infra_step=True,
        **kwargs)

  def resource_sizes(self, apk_path, chartjson_file=False,
                     upload_archives_to_bucket=None, perf_id=None):
    cmd = ['build/android/resource_sizes.py', str(apk_path)]
    if chartjson_file:
      cmd.append('--chartjson')

    config = {
        'steps': {
            'resource_sizes (%s)' % self.m.path.basename(apk_path): {
                'cmd': ' '.join(pipes.quote(x) for x in cmd),
                'device_affinity': None,
                'archive_output_dir': True
            }
        },
        'version': 1
    }
    self.run_sharded_perf_tests(
        config=self.m.json.input(config),
        flaky_config=None,
        perf_id=perf_id or self.m.properties['buildername'],
        chartjson_file=chartjson_file,
        json_output=False,
        upload_archives_to_bucket=upload_archives_to_bucket)

  def upload_apks_for_bisect(self, update_properties, bucket, path):
    """Uploads android apks for functional bisects."""
    archive_name = 'build_product.zip'
    zipfile = self.m.path['checkout'].join('out', archive_name)
    self.make_zip_archive(
      'package_apks_for_bisect',
      archive_name,
      files=['apks'],
      preserve_paths=False,
      cwd=self.m.path['checkout']
    )
    # Get the commit postion for the revision to be used in archive name,
    # if not found use the git hash.
    try:
      branch, rev = self.m.commit_position.parse(
          update_properties.get('got_revision_cp'))
    except ValueError:  # pragma: no cover
      rev = update_properties.get('got_revision')

    self.m.gsutil.upload(
        name='upload_apks_for_bisect',
        source=zipfile,
        bucket=bucket,
        dest=path % rev,
        version='4.7')

  def upload_build(self, bucket, path):
    archive_name = 'build_product.zip'

    zipfile = self.m.path['checkout'].join('out', archive_name)

    self.make_zip_archive(
      'zip_build_product',
      archive_name,
      preserve_paths=True,
      cwd=self.m.path['checkout']
    )

    self.m.gsutil.upload(
        name='upload_build_product',
        source=zipfile,
        bucket=bucket,
        dest=path,
        version='4.7')

  def download_build(self, bucket, path, extract_path=None):
    zipfile = self.m.path['checkout'].join('out', 'build_product.zip')
    self.m.gsutil.download(
        name='download_build_product',
        bucket=bucket,
        source=path,
        dest=zipfile,
        version='4.7',
    )
    extract_path = extract_path or self.m.path['checkout']
    self.m.step(
      'unzip_build_product',
      ['unzip', '-o', zipfile],
      cwd=extract_path,
      infra_step=True,
    )

  def zip_and_upload_build(self, bucket):
    # TODO(luqui): Unify make_zip_archive and upload_build with this
    # (or at least make the difference clear).
    self.m.archive.zip_and_upload_build(
        'zip_build',
        target=self.m.chromium.c.BUILD_CONFIG,
        # We send None as the path so that zip_build.py gets it from factory
        # properties.
        build_url=None,
        src_dir=self.m.path['start_dir'].join('src'),
        exclude_files='lib.target,gen,android_webview,jingle_unittests')

  def use_devil_adb(self):
    # TODO(jbudorick): Remove this after resolving
    # https://github.com/catapult-project/catapult/issues/2901
    devil_path = self.m.path['checkout'].join('third_party', 'catapult', 'devil')
    self.m.python.inline(
        'initialize devil',
        """
        import sys
        sys.path.append(sys.argv[1])
        from devil import devil_env
        devil_env.config.Initialize()
        devil_env.config.PrefetchPaths(dependencies=['adb'])
        """,
        args=[devil_path])
    self.m.adb.set_adb_path(
        devil_path.join('bin', 'deps', 'linux2', 'x86_64', 'bin', 'adb'))

  def create_adb_symlink(self):
    # Creates a sym link to the adb executable in the home dir
    self.m.python(
        'create adb symlink',
        self.m.path['checkout'].join('build', 'symlink.py'),
        ['-f', self.m.adb.adb_path(), os.path.join('~', 'adb')],
        infra_step=True)

  def spawn_logcat_monitor(self):
    self.m.step(
        'spawn_logcat_monitor',
        [self.package_repo_resource('scripts', 'slave', 'daemonizer.py'),
         '--', self.c.cr_build_android.join('adb_logcat_monitor.py'),
         self.m.chromium.c.build_dir.join('logcat'),
         self.m.adb.adb_path()],
        env=self.m.chromium.get_env(),
        infra_step=True)

  def spawn_device_monitor(self):
    script = self.package_repo_resource('scripts', 'slave', 'daemonizer.py')
    args = [
        '--action', 'restart',
        '--pid-file-path', '/tmp/device_monitor.pid', '--',
        self.m.path['checkout'].join('third_party', 'catapult', 'devil',
                                     'devil', 'android', 'tools',
                                     'device_monitor.py'),
        '--adb-path', self.m.adb.adb_path(),
        '--blacklist-file', self.blacklist_file
    ]
    self.m.python('spawn_device_monitor', script, args, infra_step=True)

  def shutdown_device_monitor(self):
    script = self.package_repo_resource('scripts', 'slave', 'daemonizer.py')
    args = [
        '--action', 'stop',
        '--pid-file-path', '/tmp/device_monitor.pid',
    ]
    self.m.python('shutdown_device_monitor', script, args, infra_step=True)

  def authorize_adb_devices(self):
    script = self.package_repo_resource(
        'scripts', 'slave', 'android', 'authorize_adb_devices.py')
    args = ['--verbose', '--adb-path', self.m.adb.adb_path()]
    return self.m.python('authorize_adb_devices', script, args, infra_step=True,
                         env=self.m.chromium.get_env())

  def detect_and_setup_devices(self, restart_usb=False, skip_wipe=False,
                               disable_location=False, min_battery_level=None,
                               disable_network=False, disable_java_debug=False,
                               reboot_timeout=None, max_battery_temp=None,
                               remove_system_webview=False):
    self.authorize_adb_devices()
    self.device_recovery()
    self.provision_devices(
      skip_wipe=skip_wipe, disable_location=disable_location,
      min_battery_level=min_battery_level, disable_network=disable_network,
      disable_java_debug=disable_java_debug, reboot_timeout=reboot_timeout,
      max_battery_temp=max_battery_temp,
      remove_system_webview=remove_system_webview)
    self.device_status()

  @property
  def blacklist_file(self):
    return self.out_path.join('bad_devices.json')


  def revert_device_file_format(self):
    # If current device file is jsonified, revert it back to original format.
    if self.m.path.exists(self.known_devices_file):
      with self.m.step.nest('fix_device_file_format'):
        file_contents = self.m.file.read(
            'read_device_file', self.known_devices_file,
            test_data='device1\ndevice2\ndevice3')
        try:
          devices = json.loads(file_contents)
          self.m.step.active_result.presentation.step_text += (
              'file format is json, reverting')
          old_format = '\n'.join(devices)
          self.m.file.write(
              'revert_device_file', self.known_devices_file, old_format)
        except ValueError:
          # File wasn't json, so no need to revert.
          self.m.step.active_result.presentation.step_text += (
              'file format is compatible')

  def device_status_check(self, restart_usb=False, **kwargs):
    # TODO(bpastene): Remove once chromium revisions prior to
    # crrev.com/1faecde0c03013b6cd725da413339c60223f8948 are no longer tested.
    # See crbug.com/619707 for context.
    self.revert_device_file_format()
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
        results = self.m.step(
            'Host Info',
            [self.m.path['checkout'].join('testing', 'scripts',
                                          'host_info.py')] + args,
            env=self.m.chromium.get_env(),
            infra_step=True,
            step_test_data=lambda: self.m.json.test_api.output({
                'valid': True,
                'failures': [],
                '_host_info': {
                    'os_system': 'os_system',
                    'os_release': 'os_release',
                    'processor': 'processor',
                    'num_cpus': 'num_cpus',
                    'free_disk_space': 'free_disk_space',
                    'python_version': 'python_version',
                    'python_path': 'python_path',
                    'devices': [{
                        "usb_status": True,
                        "blacklisted": None,
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
                }}),
            **kwargs)
      return results
    except self.m.step.InfraFailure as f:
      for failure in f.result.json.output.get('failures', []):
        f.result.presentation.logs[failure] = [failure]
      f.result.presentation.status = self.m.step.EXCEPTION

  # TODO(jbudorick): Remove restart_usb once it's unused.
  def device_recovery(self, restart_usb=False, **kwargs):
    args = [
        '--blacklist-file', self.blacklist_file,
        '--known-devices-file', self.known_devices_file,
        '--adb-path', self.m.adb.adb_path(),
        '-v'
    ]
    if self.c.restart_usb or restart_usb:
      args += ['--enable-usb-reset']
    self.m.step(
        'device_recovery',
        [self.m.path['checkout'].join('third_party', 'catapult', 'devil',
                                      'devil', 'android', 'tools',
                                      'device_recovery.py')] + args,
        env=self.m.chromium.get_env(),
        infra_step=True,
        **kwargs)

  def device_status(self, **kwargs):
    buildbot_file = '/home/chrome-bot/.adb_device_info'
    args = [
        '--json-output', self.m.json.output(),
        '--blacklist-file', self.blacklist_file,
        '--known-devices-file', self.known_devices_file,
        '--buildbot-path', buildbot_file,
        '--adb-path', self.m.adb.adb_path(),
        '-v', '--overwrite-known-devices-files',
    ]
    try:
      result = self.m.step(
          'device_status',
          [self.m.path['checkout'].join('third_party', 'catapult', 'devil',
                                        'devil', 'android', 'tools',
                                        'device_status.py')] + args,
          step_test_data=lambda: self.m.json.test_api.output([
              {
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
                "wifi_ip": "",
                "imei_slice": "Unknown",
                "ro.build.id": "LRX21O",
                "ro.build.product": "product_name",
                "build_detail":
                    "google/razor/flo:5.0/LRX21O/1570415:userdebug/dev-keys",
                "serial": "07a00ca4",
                "adb_status": "device",
                "blacklisted": False,
                "usb_status": True,
            },
            {
              "adb_status": "offline",
              "blacklisted": True,
              "serial": "03e0363a003c6ad4",
              "usb_status": False,
            },
            {
              "adb_status": "unauthorized",
              "blacklisted": True,
              "serial": "03e0363a003c6ad5",
              "usb_status": True,
            },
            {
              "adb_status": "device",
              "blacklisted": True,
              "serial": "03e0363a003c6ad6",
              "usb_status": True,
            }
          ]),
          env=self.m.chromium.get_env(),
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
          elif d['blacklisted']:
            key = '%s: blacklisted' % d['serial']
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
      params = {
        'summary': ('Device Offline on %s %s' %
          (self.m.properties['mastername'], self.m.properties['slavename'])),
        'comment': ('Buildbot: %s\n(Please do not change any labels)' %
          self.m.properties['buildername']),
        'labels': 'Restrict-View-Google,OS-Android,Infra,Infra-Labs',
      }
      link = ('https://code.google.com/p/chromium/issues/entry?%s' %
        urllib.urlencode(params))
      f.result.presentation.links.update({
        'report a bug': link
      })
      raise


  def provision_devices(self, skip_wipe=False, disable_location=False,
                        min_battery_level=None, disable_network=False,
                        disable_java_debug=False, max_battery_temp=None,
                        disable_system_chrome=False, reboot_timeout=None,
                        remove_system_webview=False, emulators=False,
                        **kwargs):
    args = [
        '--adb-path', self.m.adb.adb_path(),
        '--blacklist-file', self.blacklist_file,
        '--output-device-blacklist', self.m.json.output(add_json_log=False),
        '-t', self.m.chromium.c.BUILD_CONFIG,
    ]
    if skip_wipe:
      args.append('--skip-wipe')
    if disable_location:
      args.append('--disable-location')
    if reboot_timeout is not None:
      assert isinstance(reboot_timeout, int)
      assert reboot_timeout > 0
      args.extend(['--reboot-timeout', reboot_timeout])
    if min_battery_level is not None:
      assert isinstance(min_battery_level, int)
      assert min_battery_level >= 0
      assert min_battery_level <= 100
      args.extend(['--min-battery-level', min_battery_level])
    if disable_network:
      args.append('--disable-network')
    if disable_java_debug:
      args.append('--disable-java-debug')
    if max_battery_temp:
      assert isinstance(max_battery_temp, int)
      assert max_battery_temp >= 0
      assert max_battery_temp <= 500
      args.extend(['--max-battery-temp', max_battery_temp])
    if disable_system_chrome:
      args.append('--disable-system-chrome')
    if remove_system_webview:
      args.append('--remove-system-webview')
    if self.c and self.c.chrome_specific_wipe:
      args.append('--chrome-specific-wipe')
    if emulators:
      args.append('--emulators')
    if self.c and self.c.use_devil_provision:
      provision_path = self.m.path['checkout'].join(
          'third_party', 'catapult', 'devil', 'devil', 'android', 'tools',
          'provision_devices.py')
    else:
      provision_path = self.m.path['checkout'].join(
          'build', 'android', 'provision_devices.py')
    result = self.m.python(
      'provision_devices',
      provision_path,
      args=args,
      env=self.m.chromium.get_env(),
      infra_step=True,
      **kwargs)

  def apk_path(self, apk):
    return self.m.chromium.output_dir.join('apks', apk) if apk else None

  def adb_install_apk(self, apk, allow_downgrade=False, keep_data=False,
                      devices=None):
    install_cmd = [
        self.m.path['checkout'].join('build',
                                     'android',
                                     'adb_install_apk.py'),
        apk, '-v', '--blacklist-file', self.blacklist_file,
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
    return self.m.step('install ' + self.m.path.basename(apk), install_cmd,
                       infra_step=True,
                       env=self.m.chromium.get_env())

  def _asan_device_setup(self, args):
    script = self.m.path['checkout'].join(
        'tools', 'android', 'asan', 'third_party', 'asan_device_setup.sh')
    cmd = [script] + args
    env = dict(self.m.chromium.get_env())
    env['ADB'] = self.m.adb.adb_path()
    for d in self.devices:
      self.m.step(d,
                  cmd + ['--device', d],
                  infra_step=True,
                  env=env)
    self.wait_for_devices(self.devices)

  def wait_for_devices(self, devices):
    script = self.m.path['checkout'].join(
        'third_party', 'catapult', 'devil', 'devil', 'android', 'tools',
        'wait_for_devices.py')
    args = [
        '--adb-path', self.m.adb.adb_path(),
        '-v'
    ]
    args += devices
    self.m.python('wait_for_devices', script, args, infra_step=True)

  def asan_device_setup(self):
    clang_version_cmd = [
        self.m.path['checkout'].join('tools', 'clang', 'scripts', 'update.py'),
        '--print-clang-version'
    ]
    clang_version_step = self.m.step('get_clang_version',
        clang_version_cmd,
        stdout=self.m.raw_io.output_text(),
        step_test_data=(
            lambda: self.m.raw_io.test_api.stream_output('1.1.1')))
    clang_version = clang_version_step.stdout.strip()
    with self.m.step.nest('Set up ASAN on devices'):
      self.m.adb.root_devices()
      args = [
          '--lib',
          self.m.path['checkout'].join(
              'third_party', 'llvm-build', 'Release+Asserts', 'lib', 'clang',
              clang_version, 'lib', 'linux', 'libclang_rt.asan-arm-android.so')
      ]
      self._asan_device_setup(args)

  def asan_device_teardown(self):
    with self.m.step.nest('Tear down ASAN on devices'):
      self._asan_device_setup(['--revert'])

  def monkey_test(self, **kwargs):
    args = [
        'monkey',
        '-v',
        '--browser=%s' % self.c.channel,
        '--event-count=50000',
        '--blacklist-file', self.blacklist_file,
    ]
    return self.test_runner(
        'Monkey Test',
        args,
        env={'BUILDTYPE': self.c.BUILD_CONFIG},
        **kwargs)


  def _run_sharded_tests(self,
                         config='sharded_perf_tests.json',
                         flaky_config=None,
                         chartjson_output=False,
                         json_output=True,
                         max_battery_temp=None,
                         known_devices_file=None,
                         enable_platform_mode=False,
                         write_buildbot_json=False,
                         num_retries=0,
                         test_trace=None,
                         **kwargs):
    args = [
        'perf',
        '--release',
        '--verbose',
        '--steps', config,
        '--blacklist-file', self.blacklist_file,
        '--num-retries', num_retries
    ]
    if flaky_config:
      args.extend(['--flaky-steps', flaky_config])
    if chartjson_output:
      args.append('--collect-chartjson-data')
    if json_output:
      args.append('--collect-json-data')
    if max_battery_temp:
      args.extend(['--max-battery-temp', max_battery_temp])
    if known_devices_file:
      args.extend(['--known-devices-file', known_devices_file])
    if enable_platform_mode:
      args.extend(['--enable-platform-mode'])
    if write_buildbot_json:
      args.extend(['--write-buildbot-json'])
    if test_trace:
      args.extend(['--trace-output', test_trace])

    self.test_runner(
        'Sharded Perf Tests',
        args,
        cwd=self.m.path['checkout'],
        env=self.m.chromium.get_env(),
        **kwargs)

  def run_sharded_perf_tests(self, config, flaky_config=None, perf_id=None,
                             test_type_transform=lambda x: x,
                             chartjson_file=False, max_battery_temp=None,
                             upload_archives_to_bucket=None,
                             known_devices_file=None,
                             enable_platform_mode=False,
                             timestamp_as_point_id=False,
                             pass_adb_path=True,
                             num_retries=0,
                             json_output=True, **kwargs):
    """Run the perf tests from the given config file.

    config: the path of the config file containing perf tests.
    flaky_config: optional file of tests to avoid.
    perf_id: the id of the builder running these tests
    test_type_transform: a lambda transforming the test name to the
      test_type to upload to.
    known_devices_file: Path to file containing serial numbers of known devices.
    enable_platform_mode: If set, will run using the android test runner's new
      platform mode.
    timestamp_as_point_id: If True, will use a unix timestamp as a point_id to
      identify values in the perf dashboard; otherwise the default (commit
      position) is used.
    pass_adb_path: If True, will pass the configured adb binary to the test
      runner via --adb-path.
    """

    with self.m.tempfile.temp_dir('test_runner_trace') as trace_dir:
      test_trace_path = self.m.path.join(trace_dir, 'test_trace.html')

      # TODO(jbudorick): Remove pass_adb_path once telemetry can use a
      # configurable adb path.

      # test_runner.py actually runs the tests and records the results
      self._run_sharded_tests(config=config, flaky_config=flaky_config,
                              chartjson_output=chartjson_file,
                              json_output=json_output,
                              max_battery_temp=max_battery_temp,
                              known_devices_file=known_devices_file,
                              enable_platform_mode=enable_platform_mode,
                              pass_adb_path=pass_adb_path,
                              num_retries=num_retries,
                              test_trace=test_trace_path, **kwargs)

      # now upload test trace.
      dest = '{builder}/trace_{buildno}.html'.format(
          builder=self.m.properties['buildername'],
          buildno=self.m.properties['buildnumber'])
      self.m.gsutil.upload(
          name='Upload Test Trace',
          source=test_trace_path,
          bucket='chromium-testrunner-trace',
          dest=dest,
          link_name='Test Trace')

    # now obtain the list of tests that were executed.
    result = self.test_runner(
        'get perf test list',
        ['perf', '--steps', config, '--output-json-list', self.m.json.output(),
         '--blacklist-file', self.blacklist_file],
        step_test_data=lambda: self.m.json.test_api.output([
            {'test': 'perf_test.foo', 'device_affinity': 0,
             'end_time': 1443438432.949711, 'has_archive': True},
            {'test': 'perf_test.foo.reference', 'device_affinity': 0},
            {'test': 'page_cycler.foo', 'device_affinity': 0}]),
        env=self.m.chromium.get_env()
    )
    perf_tests = result.json.output

    if perf_tests and isinstance(perf_tests[0], dict):
      perf_tests = sorted(perf_tests,
          key=lambda x: (x['device_affinity'], x['test']))
    else:
      # TODO(phajdan.jr): restore coverage after moving to chromium/src .
      perf_tests = [{'test': v} for v in perf_tests]  # pragma: no cover

    failures = []
    for test_data in perf_tests:
      test_name = str(test_data['test'])  # un-unicode
      test_type = test_type_transform(test_name)
      annotate = self.m.chromium.get_annotate_by_test_name(test_name)
      test_end_time = int(test_data.get('end_time', 0))
      if not test_end_time:
        test_end_time = int(self.m.time.time())
      point_id = test_end_time if timestamp_as_point_id else None

      if upload_archives_to_bucket and test_data.get('has_archive'):
        archive = self.m.path.mkdtemp('perf_archives').join('output_dir.zip')
      else:
        archive = None
      print_step_cmd = ['perf', '--print-step', test_name, '--verbose',
                        '--adb-path', self.m.adb.adb_path(),
                        '--blacklist-file', self.blacklist_file]
      if archive:
        print_step_cmd.extend(['--get-output-dir-archive', archive])
      if enable_platform_mode:
        print_step_cmd.extend(['--enable-platform-mode'])

      # JSON output is used to determine which individual pages failed.
      if json_output:
        print_step_cmd.extend(
            ['--output-json-data', self.m.json.output(name='output_json')])

      example_output_json = {
        'format_version': '0.2',
        'summary_values': [],
        'per_page_values': [
          {
            'name': 'network_data_sent',
            'type': 'failure',
            'page_id': 0
          },
          {
            'name': 'network_data_sent',
            'type': 'failure',
            'page_id': 1
          },
          {
            'name': 'network_data_sent',
            'type': 'failure',
            'page_id': 2
          }
        ],
        'benchmark_metadata': {
          'rerun_options': [],
          'type': 'telemetry_benchmark',
          'name': 'example.example',
          'description': 'Example perf test.'
        },
        'pages': {
          '0': {
            'name': 'failing_page_name',
            'id': 0
          },
          '1': {
            'url': 'www.failing_webpage.com',
            'id': 1
          },
          '2': {
            'id': 2
          }
        },
        'next_version': '0.3',
        'benchmark_name': 'example.example'
      }

      try:
        with self.handle_exit_codes():
          env = self.m.chromium.get_env()
          env['CHROMIUM_OUTPUT_DIR'] = self.m.chromium.output_dir
          self.m.chromium.runtest(
            self.c.test_runner,
            print_step_cmd,
            name=test_name,
            perf_dashboard_id=test_type,
            point_id=point_id,
            test_type=test_type,
            annotate=annotate,
            results_url='https://chromeperf.appspot.com',
            perf_id=perf_id,
            env=env,
            chartjson_file=chartjson_file,
            step_test_data=(
                lambda: self.m.json.test_api.output([]) +
                        self.m.json.test_api.output(
                            example_output_json, name='output_json')))
      except self.m.step.StepFailure as f:
        # Only warn for failures on reference builds.
        if test_name.endswith('.reference'):
          if f.result.presentation.status == self.m.step.FAILURE:
            f.result.presentation.status = self.m.step.WARNING
          else:
            failures.append(f)
        else:
          failures.append(f)
      finally:
        step_result = self.m.step.active_result

        if (hasattr(step_result, 'json') and
            hasattr(step_result.json, 'outputs')):

          json_results = step_result.json.outputs.get('output_json')
          if json_results:
            failed_pages = []
            pages_info = json_results.get('pages', {})

            for value in json_results.get('per_page_values', []):
              if value.get('type') == 'failure':
                failed_page_info = pages_info.get(str(value.get('page_id')), {})
                if failed_page_info.get('name'):
                  failed_pages.append(failed_page_info.get('name'))
                elif failed_page_info.get('url'):
                  failed_pages.append(failed_page_info.get('url'))
                else:
                  failed_pages.append(
                      'page_id:%s' % value.get('page_id', 'unknown'))

            step_result.presentation.step_text += (
                self.m.test_utils.format_step_text(
                    [['failures:', failed_pages]]))

        if 'device_affinity' in test_data:
          step_result.presentation.step_text += (
              self.m.test_utils.format_step_text(
                  [['Device Affinity: %s' % test_data['device_affinity']]]))

      if archive:
        dest = '{builder}/{test}/{timestamp}_build_{buildno}.zip'.format(
          builder=self.m.properties['buildername'],
          test=test_name,
          timestamp=_TimestampToIsoFormat(test_end_time),
          buildno=self.m.properties['buildnumber'])
        self.m.gsutil.upload(
          name='upload %s output dir archive' % test_name,
          source=archive,
          bucket=upload_archives_to_bucket,
          dest=dest,
          link_name='output_dir.zip')

    if failures:
      raise self.m.step.StepFailure('sharded perf tests failed %s' % failures)

  def run_telemetry_browser_test(self, test_name, browser='android-chromium'):
    """Run a telemetry browser test."""
    try:
      self.m.python(
          name='Run telemetry browser_test %s' % test_name,
          script=self.m.path['checkout'].join(
              'chrome', 'test', 'android', 'telemetry_tests',
              'run_chrome_browser_tests.py'),
          args=['--browser=%s' % browser,
                '--write-abbreviated-json-results-to', self.m.json.output(),
                test_name],
          step_test_data=lambda: self.m.json.test_api.output(
              {'successes': ['passed_test1']}))
    finally:
      test_failures = self.m.step.active_result.json.output.get('failures', [])
      self.m.step.active_result.presentation.step_text += (
          self.m.test_utils.format_step_text(
              [['failures:', test_failures]]))

  def run_instrumentation_suite(self,
                                name,
                                test_apk=None,
                                apk_under_test=None,
                                additional_apks=None,
                                flakiness_dashboard=None,
                                annotation=None, except_annotation=None,
                                screenshot=False, verbose=False, tool=None,
                                apk_package=None,
                                json_results_file=None,
                                timeout_scale=None, strict_mode=None,
                                suffix=None, num_retries=None,
                                device_flags=None,
                                wrapper_script_suite_name=None,
                                result_details=False,
                                cs_base_url=None,
                                store_tombstones=False,
                                render_results_dir=None,
                                args=None,
                                **kwargs):
    args = args or []
    args.extend(['--blacklist-file', self.blacklist_file,])
    if tool:
      args.append('--tool=%s' % tool)
    if flakiness_dashboard:
      args.extend(['--flakiness-dashboard-server', flakiness_dashboard])
    if annotation:
      args.extend(['-A', annotation])
    if except_annotation:
      args.extend(['-E', except_annotation])
    if screenshot:
      args.append('--screenshot')
    if verbose:
      args.append('--verbose')
    if self.c.coverage or self.c.incremental_coverage:
      args.extend(['--coverage-dir', self.coverage_dir])
    if result_details and not json_results_file:
      json_results_file = self.m.test_utils.gtest_results(add_json_log=False)
    if json_results_file:
      args.extend(['--json-results-file', json_results_file])
    if store_tombstones:
      args.append('--store-tombstones')
    if timeout_scale:
      args.extend(['--timeout-scale', timeout_scale])
    if strict_mode:
      args.extend(['--strict-mode', strict_mode])
    if num_retries is not None:
      args.extend(['--num-retries', str(num_retries)])
    if device_flags:
      args.extend(['--device-flags-file', device_flags])
    if test_apk:
      args.extend(['--test-apk', test_apk])
    if apk_under_test:
      args.extend(['--apk-under-test', apk_under_test])
    for a in additional_apks or []:
      args.extend(['--additional-apk', a])

    if not wrapper_script_suite_name:
      args.insert(0, 'instrumentation')
      if self.m.chromium.c.BUILD_CONFIG == 'Release':
        args.append('--release')

    step_name = '%s%s' % (
        annotation or name, ' (%s)' % suffix if suffix else '')

    try:
      step_result = self.test_runner(
          step_name,
          args=args,
          wrapper_script_suite_name=wrapper_script_suite_name,
          **kwargs)
    finally:
      result_step = self.m.step.active_result
      if render_results_dir:
        self._upload_render_test_failures(render_results_dir)
      if result_details:
        if (hasattr(result_step, 'test_utils') and
            hasattr(result_step.test_utils, 'gtest_results')):
          json_results = self.m.json.input(
              result_step.test_utils.gtest_results.raw)
          details = self.create_result_details(step_name,
                                               json_results,
                                               cs_base_url)
          self.m.step.active_result.presentation.logs['result_details'] = (
              details)
      # Need to copy gtest results over. A few places call
      # |run_instrumentation_suite| function and then look for results in
      # the active_result.
      self.copy_gtest_results(result_step, self.m.step.active_result)
    return step_result

  def copy_gtest_results(self, result_step, active_step):
    if (hasattr(result_step, 'test_utils') and
        hasattr(result_step.test_utils, 'gtest_results')):
      active_step.test_utils = result_step.test_utils

  def create_result_details(self, step_name, json_results_file, cs_base_url):
    presentation_args = ['--json-file',
                         json_results_file,
                         '--master-name',
                         self.m.properties.get('mastername')]
    if cs_base_url:
      presentation_args.extend(['--cs-base-url', cs_base_url])
    result_details = self.m.python(
        '%s: generate result details' % step_name,
        self.resource('test_results_presentation.py'),
        args=presentation_args,
        stdout=self.m.raw_io.output_text(),
        step_test_data=(
            lambda: self.m.raw_io.test_api.stream_output(
                '<!DOCTYPE html><html></html>')))
    return result_details.stdout.splitlines()

  def _upload_render_test_failures(self, render_results_dir):
    """Uploads render test results. Generates HTML file displaying results."""
    args = ['--output-html-file', self.m.raw_io.output_text(),
            '--buildername', self.m.properties['buildername'],
            '--build-number', self.m.properties['buildnumber'],
            '--render-results-dir', render_results_dir]
    step_result = self.m.python(
        name='[Render Tests] Upload Results',
        script=self.m.path['checkout'].join(
            'build', 'android', 'render_tests',
            'process_render_test_results.py'),
        args=args,
        step_test_data=lambda: self.m.raw_io.test_api.output_text(
            '<!DOCTYPE html><html></html>'))
    step_result.presentation.logs['render results'] = (
        step_result.raw_io.output_text.splitlines())

  def logcat_dump(self, gs_bucket=None):
    if gs_bucket:
      log_path = self.m.chromium.output_dir.join('full_log')
      self.m.python(
          'logcat_dump',
          self.m.path['checkout'].join('build', 'android',
                                       'adb_logcat_printer.py'),
          [ '--output-path', log_path,
            self.m.path['checkout'].join('out', 'logcat') ],
          infra_step=True)
      if self.m.tryserver.is_tryserver and not self.c.INTERNAL:
        args = ['-a', 'public-read']
      else:
        args = []
      self.m.gsutil.upload(
          log_path,
          gs_bucket,
          'logcat_dumps/%s/%s' % (self.m.properties['buildername'],
                                  self.m.properties['buildnumber']),
          args=args,
          link_name='logcat dump',
          version='4.7',
          parallel_upload=True)

    else:
      self.m.python(
          'logcat_dump',
          self.package_repo_resource('scripts', 'slave', 'tee.py'),
          [self.m.chromium.output_dir.join('full_log'),
           '--',
           self.m.path['checkout'].join('build', 'android',
                                        'adb_logcat_printer.py'),
           self.m.path['checkout'].join('out', 'logcat')],
          infra_step=True,
          )

  def generate_breakpad_symbols(
      self, symbols_dir, binary_path, root_chromium_dir):
    """Generate breakpad symbols.

    This step requires dump_syms binary to exist in the build dir.

    Args:
      symbols_dir: The directory to dump the breakpad symbols to.
      binary_path: Path to binary to generate symbols for.
      root_chromium_dir: Root Chromium directory.
    """
    build_dir = root_chromium_dir.join(
        'out', self.m.chromium.c.BUILD_CONFIG)

    generate_symbols_args = ['--symbols-dir', symbols_dir,
                             '--build-dir', build_dir,
                             '--binary', binary_path]
    self.m.python(('generate breakpad symbols for %s'
                   % self.m.path.basename(binary_path)),
                  root_chromium_dir.join(
                      'components', 'crash', 'content',
                      'tools', 'generate_breakpad_symbols.py'),
                  generate_symbols_args)

  def stackwalker(self, root_chromium_dir, binary_paths):
    """Runs stack walker tool to symbolize breakpad crashes.

    This step requires logcat file. The logcat monitor must have
    been run on the bot.

    Args:
      binary_paths: Paths to binaries to generate breakpad symbols.
      root_chromium_dir: Root Chromium directory.
    """
    build_dir = root_chromium_dir.join(
        'out', self.m.chromium.c.BUILD_CONFIG)
    logcat = build_dir.join('full_log')

    microdump_stackwalk_path = build_dir.join('microdump_stackwalk')
    if not self.m.path.exists(microdump_stackwalk_path):
      result = self.m.step('no microdump stackwalk', ['echo', build_dir])
      result.presentation.logs['info'] = [
          'This bot appears to not have the microdump_stackwalk binary.',
          'This is needed by the bot to run stack walking logic for android'
          'builds.',
          'No action is needed at this time; contact martiniss@ for any'
          ' questions or issues',
      ]
      return

    with self.m.tempfile.temp_dir('symbols') as temp_symbols_dir:
      # TODO(mikecase): Only generate breakpad symbols if we
      # know there is at least one breakpad crash. This step takes
      # several minutes and we should only run it if we need to.
      for binary in binary_paths:
        self.generate_breakpad_symbols(
            temp_symbols_dir, binary, root_chromium_dir)
      stackwalker_args = ['--stackwalker-binary-path',
                          microdump_stackwalk_path,
                          '--stack-trace-path', logcat,
                          '--symbols-path', temp_symbols_dir]
      self.m.python('symbolized breakpad crashes',
                    root_chromium_dir.join(
                        'build', 'android', 'stacktrace', 'stackwalker.py'),
                    stackwalker_args)

  def stack_tool_steps(self, force_latest_version=False):
    build_dir = self.m.path['checkout'].join('out',
                                             self.m.chromium.c.BUILD_CONFIG)
    log_file = build_dir.join('full_log')
    target_arch = self.m.chromium.c.gyp_env.GYP_DEFINES['target_arch']
    # gyp converts ia32 to x86, bot needs to do the same
    target_arch = {'ia32': 'x86'}.get(target_arch) or target_arch

    # --output-directory hasn't always exited on these scripts, so use the
    # CHROMIUM_OUTPUT_DIR environment variable to avoid unrecognized flag
    # failures on older script versions (e.g. when doing bisects).
    # TODO(agrieve): Switch to --output-directory once we don't need bisects
    #     to be able to try revisions that happened before Feb 2016.
    env = self.m.chromium.get_env()
    env['CHROMIUM_OUTPUT_DIR'] = str(build_dir)
    self.m.step(
        'stack_tool_with_logcat_dump',
        [self.m.path['checkout'].join('third_party', 'android_platform',
                              'development', 'scripts', 'stack'),
         '--arch', target_arch, '--more-info', log_file],
        env=env,
        infra_step=True)
    tombstones_cmd = [
        self.m.path['checkout'].join('build', 'android', 'tombstones.py'),
        '-a', '-s', '-w',
    ]
    if (force_latest_version or
        int(self.m.chromium.get_version().get('MAJOR', 0)) > 52):
      tombstones_cmd += ['--adb-path', self.m.adb.adb_path()]
    self.m.step(
        'stack_tool_for_tombstones',
        tombstones_cmd,
        env=env,
        infra_step=True)
    if self.c.asan_symbolize:
      self.m.step(
          'stack_tool_for_asan',
          [self.m.path['checkout'].join('build',
                                        'android',
                                        'asan_symbolize.py'),
           '-l', log_file],
          env=env,
          infra_step=True)

  def test_report(self):
    self.m.python.inline(
        'test_report',
         """
            import glob, os, sys
            for report in glob.glob(sys.argv[1]):
              with open(report, 'r') as f:
                for l in f.readlines():
                  print l
              os.remove(report)
         """,
         args=[self.m.path['checkout'].join('out',
                                            self.m.chromium.c.BUILD_CONFIG,
                                            'test_logs',
                                            '*.log')],
    )

  def common_tests_setup_steps(self, perf_setup=False,
                               remove_system_webview=False, skip_wipe=False):
    if self.c.use_devil_adb:
      self.use_devil_adb()
    self.create_adb_symlink()
    self.spawn_logcat_monitor()
    self.spawn_device_monitor()
    self.authorize_adb_devices()
    # TODO(jbudorick): Restart USB only on perf bots while we
    # figure out the fate of the usb reset in general.
    self.device_recovery(restart_usb=perf_setup)
    if perf_setup:
      kwargs = {
          'min_battery_level': 95,
          'disable_network': True,
          'disable_java_debug': True,
          'max_battery_temp': 350}
    else:
      kwargs = {}
    if skip_wipe:
      kwargs['skip_wipe'] = True
    self.provision_devices(remove_system_webview=remove_system_webview,
                           **kwargs)
    self.device_status()
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan', 0) == 1:
      self.asan_device_setup()

  def common_tests_final_steps(self, logcat_gs_bucket='chromium-android',
                               force_latest_version=False, checkout_dir=None,
                               uses_webview=False):
    self.shutdown_device_monitor()
    self.logcat_dump(gs_bucket=logcat_gs_bucket)
    self.stack_tool_steps(force_latest_version)
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan', 0) == 1:
      self.asan_device_teardown()
    self.test_report()

    if checkout_dir:
      binary_dir = self.m.chromium.output_dir.join('lib.unstripped')
      breakpad_binaries = [binary_dir.join('libchrome.so')]
      if uses_webview:
        breakpad_binaries.append(binary_dir.join('libwebviewchromium.so'))
      self.stackwalker(
          root_chromium_dir=checkout_dir,
          binary_paths=breakpad_binaries)

  def android_build_wrapper(self, logcat_gs_bucket='chromium-android'):
    @contextlib.contextmanager
    def wrapper(api):
      """A context manager for use as auto_bisect's build_context_mgr.

      This wraps every overall bisect run.
      """
      try:
        self.common_tests_setup_steps(
            perf_setup=True, remove_system_webview=True)
        api.chromium.runhooks()

        yield
      finally:
        self.common_tests_final_steps(logcat_gs_bucket=logcat_gs_bucket)
    return wrapper

  def android_test_wrapper(self, _logcat_gs_bucket='chromium-android'):
    @contextlib.contextmanager
    def wrapper(_api):
      """A context manager for running android test steps."""
      yield
    return wrapper

  def run_bisect_script(self, extra_src='', path_to_config='', **kwargs):
    self.m.step('prepare bisect perf regression',
        [self.m.path['checkout'].join('tools',
                                      'prepare-bisect-perf-regression.py'),
         '-w', self.m.path['start_dir']])

    args = []
    if extra_src:
      args = args + ['--extra_src', extra_src]
    if path_to_config:
      args = args + ['--path_to_config', path_to_config]
    self.m.step('run bisect perf regression',
        [self.m.path['checkout'].join('tools',
                                      'run-bisect-perf-regression.py'),
         '-w', self.m.path['start_dir']] + args, **kwargs)

  def run_test_suite(self, suite, verbose=True, gtest_filter=None, tool=None,
                     result_details=False, store_tombstones=False, name=None,
                     json_results_file=None, shard_timeout=None, args=None,
                     **kwargs):
    args = args or []
    args.extend(['--blacklist-file', self.blacklist_file])
    if verbose:
      args.append('--verbose')
    if gtest_filter:
      args.append('--gtest_filter=%s' % gtest_filter)
    if tool:
      args.append('--tool=%s' % tool)
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
      self.test_runner(
          step_name,
          args=args,
          wrapper_script_suite_name=suite,
          env=self.m.chromium.get_env(),
          **kwargs)
    finally:
      result_step = self.m.step.active_result
      if result_details:
        if (hasattr(result_step, 'test_utils') and
            hasattr(result_step.test_utils, 'gtest_results')):
          json_results = self.m.json.input(
              result_step.test_utils.gtest_results.raw)
          details = self.create_result_details(step_name,
                                               json_results,
                                               None)
          self.m.step.active_result.presentation.logs[
              'result_details'] = details
        self.copy_gtest_results(result_step,
                                self.m.step.active_result)

  def run_java_unit_test_suite(self, suite, verbose=True,
                               json_results_file=None, suffix=None, **kwargs):
    args = []
    if verbose:
      args.append('--verbose')
    if self.c.BUILD_CONFIG == 'Release':
      args.append('--release')
    if json_results_file:
      args.extend(['--json-results-file', json_results_file])

    return self.test_runner(
        '%s%s' % (str(suite), ' (%s)' % suffix if suffix else ''),
        ['junit', '-s', suite] + args,
        env=self.m.chromium.get_env(),
        **kwargs)

  def _set_webview_command_line(self, command_line_args):
    """Set the Android WebView command line.

    Args:
      command_line_args: A list of command line arguments you want set for
          webview.
    """
    command_line_script_args = [
        '--adb-path', self.m.adb.adb_path(),
        '--name', 'webview-command-line',
    ]
    command_line_script_args.extend(command_line_args)
    self.m.python('write webview command line file',
                  self.m.path['checkout'].join(
                      'build', 'android', 'adb_command_line.py'),
                  command_line_script_args)

  def run_webview_cts(self, command_line_args=None, suffix=None,
                      android_platform='L', arch='arm_64'):
    suffix = ' (%s)' % suffix if suffix else ''
    if command_line_args:
      self._set_webview_command_line(command_line_args)

    json_results_file = self.m.test_utils.gtest_results(add_json_log=False)

    cts_runner_args = ['--arch', arch,
                       '--platform', android_platform,
                       '--skip-expected-failures',
                       '--apk-dir', self.m.path['cache'],
                       '--json-results-file', json_results_file,
                       '--verbose']

    try:
      self.m.python(
          'Run CTS%s' % suffix,
          self.m.path['checkout'].join(
              'android_webview', 'tools', 'run_cts.py'),
          cts_runner_args,
          step_test_data=lambda: (
              self.m.test_utils.test_api.canned_gtest_output(passing=False)))

    finally:
      step_result = self.m.step.active_result
      if (hasattr(step_result, 'test_utils') and
          hasattr(step_result.test_utils, 'gtest_results')):
        gtest_results = step_result.test_utils.gtest_results
        step_result.presentation.step_text += (
            self.m.test_utils.format_step_text(
                [['failures:', gtest_results.failures]]))

  def coverage_report(self, upload=True, **kwargs):
    """Creates an EMMA HTML report and optionally uploads it to storage bucket.

    Creates an EMMA HTML report using generate_emma_html.py, and uploads the
    HTML report to the chrome-code-coverage storage bucket if |upload| is True.

    Args:
      upload: Uploads EMMA HTML report to storage bucket unless False is passed
        in.
      **kwargs: Kwargs for python and gsutil steps.
    """
    assert self.c.coverage or self.c.incremental_coverage, (
        'Trying to generate coverage report but coverage is not enabled')

    self.m.python(
        'Generate coverage report',
        self.m.path['checkout'].join(
            'build', 'android', 'generate_emma_html.py'),
        args=['--coverage-dir', self.coverage_dir,
              '--metadata-dir', self.out_path.join(self.c.BUILD_CONFIG),
              '--cleanup',
              '--output', self.coverage_dir.join('coverage_html',
                                                 'index.html')],
        infra_step=True,
        **kwargs)

    if upload:
      output_zip = self.coverage_dir.join('coverage_html.zip')
      self.m.zip.directory(step_name='Zip generated coverage report files',
                           directory=self.coverage_dir.join('coverage_html'),
                           output=output_zip)
      gs_dest = 'java/%s/%s/' % (
          self.m.properties['buildername'], self.m.properties['revision'])
      self.m.gsutil.upload(
          source=output_zip,
          bucket='chrome-code-coverage',
          dest=gs_dest,
          name='upload coverage report',
          link_name='Coverage report',
          version='4.7',
          **kwargs)

  def incremental_coverage_report(self):
    """Creates an incremental code coverage report.

    Generates a JSON file containing incremental coverage stats. Requires
    |file_changes_path| to contain a file with a valid JSON object.
    """
    step_result = self.m.python(
        'Incremental coverage report',
        self.m.path.join('build', 'android', 'emma_coverage_stats.py'),
        cwd=self.m.path['checkout'],
        args=['-v',
              '--out', self.m.json.output(),
              '--emma-dir', self.coverage_dir.join('coverage_html'),
              '--lines-for-coverage', self.file_changes_path],
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
        })
    )

    if step_result.json.output:
      covered_lines = step_result.json.output['patch']['incremental']['covered']
      total_lines = step_result.json.output['patch']['incremental']['total']
      percentage = covered_lines * 100.0 / total_lines if total_lines else 0

      step_result.presentation.properties['summary'] = (
          'Test coverage for this patch: %s/%s lines (%s%%).' % (
            covered_lines,
            total_lines,
            int(percentage),
        )
      )

      step_result.presentation.properties['moreInfoURL'] = self.m.url.join(
          self.m.properties['buildbotURL'],
          'builders',
          self.m.properties['buildername'],
          'builds',
          self.m.properties['buildnumber'] or '0',
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
      lines = self.m.file.read(
          ('Finding lines changed in added file %s' % new_file),
          new_file,
          test_data='int n = 0;\nn++;\nfor (int i = 0; i < n; i++) {'
      )
      file_changes[new_file] = range(1, len(lines.splitlines()) + 1)

    changed_files = self.staged_files_matching_filter('M')
    for changed_file in changed_files:
      blame = self.m.git(
          'blame', '-l', '-s', changed_file,
          stdout=self.m.raw_io.output_text(),
          name='Finding lines changed in modified file %s' % changed_file,
          step_test_data=(
              lambda: self.m.raw_io.test_api.stream_output(
                  'int n = 0;\nn++;\nfor (int i = 0; i < n; i++) {'))
      )
      blame_lines = blame.stdout.splitlines()
      file_changes[changed_file] = [i + 1 for i, line in enumerate(blame_lines)
                                    if line.startswith(blame_cached_revision)]

    self.m.file.write(
        'Saving changed lines for revision.',
        self.file_changes_path,
        self.m.json.dumps(file_changes)
    )

  def staged_files_matching_filter(self, diff_filter):
    """Returns list of files changed matching the provided diff-filter.

    Args:
      diff_filter: A string to be used as the diff-filter.

    Returns:
      A list of file paths (strings) matching the provided |diff-filter|.
    """
    diff = self.m.git(
        'diff', '--staged', '--name-only', '--diff-filter', diff_filter,
        stdout=self.m.raw_io.output_text(),
        name='Finding changed files matching diff filter: %s' % diff_filter,
        step_test_data=(
            lambda: self.m.raw_io.test_api.stream_output(
                'fake/file1.java\nfake/file2.java;\nfake/file3.java'))
    )
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

  def test_runner(self, step_name, args=None, wrapper_script_suite_name=None,
                  pass_adb_path=True, **kwargs):
    """Wrapper for the python testrunner script.

    Args:
      step_name: Name of the step.
      args: Testrunner arguments.
    """
    if not args: # pragma: no cover
      args = []
    if pass_adb_path:
      args.extend(['--adb-path', self.m.adb.adb_path()])
    with self.handle_exit_codes():
      script = self.c.test_runner
      if wrapper_script_suite_name:
        script = self.m.chromium.output_dir.join('bin', 'run_%s' %
                                                 wrapper_script_suite_name)
      else:
        env = kwargs.get('env', {})
        env['CHROMIUM_OUTPUT_DIR'] = env.get('CHROMIUM_OUTPUT_DIR',
                                             self.m.chromium.output_dir)
        kwargs['env'] = env
      return self.m.python(step_name, script, args, **kwargs)
