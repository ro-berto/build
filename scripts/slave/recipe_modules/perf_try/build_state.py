# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import uuid

# This is a wrapper class of revision that stores its build path and
# queries its status. Part of the code are adapted from the RevisionState
# class from auto-bisect module

SERVICE_ACCOUNT = 'chromium-bisect'

class BuildState(object):

  def __init__(self, api, commit_hash, with_patch):
    super(BuildState, self).__init__()
    self.api = api
    self.commit_hash = str(commit_hash)
    self.with_patch = with_patch
    if api.m.properties.get('is_test'):
      self._patch_hash = with_patch * '_123456'
    else:
      self._patch_hash = (
          with_patch * ('_' + str(uuid.uuid4()))) # pragma: no cover
    self.build_id = None
    if self.with_patch:
      self.bucket = 'chrome-perf-tryjob'
    else:
      self.bucket = 'chrome-perf'
    self.build_file_path = self._get_build_file_path()

  def _get_build_file_path(self):
    revision_suffix = '%s.zip' % (self.commit_hash + self._patch_hash)
    return self._get_platform_gs_prefix() + revision_suffix

  def _get_platform_gs_prefix(self): # pragma: no cover
    bot_name = self.api.m.properties.get('buildername', '')
    if 'win' in bot_name:
      if any(b in bot_name for b in ['x64', 'gpu']):
        return 'gs://%s/Win x64 Builder/full-build-win32_' % self.bucket
      return 'gs://%s/Win Builder/full-build-win32_' % self.bucket
    if 'android' in bot_name:
      if 'nexus9' in bot_name or 'nexus5x' in bot_name:
        return 'gs://%s/Android arm64 Builder/full-build-linux_' % self.bucket
      return 'gs://%s/Android Builder/full-build-linux_' % self.bucket
    if 'mac' in bot_name:
      return 'gs://%s/Mac Builder/full-build-mac_' % self.bucket
    return 'gs://%s/Linux Builder/full-build-linux' % self.bucket

  def _is_completed(self):
    result = self.api.m.buildbucket.get_build(
        self.build_id,
        step_test_data=lambda: self.api.m.json.test_api.output_stream(
            {'build': {'status': 'COMPLETED'}}
        ))
    return result.stdout['build']['status'] == 'COMPLETED'

  def _is_build_successful(self): # pragma: no cover
    result = self.api.m.buildbucket.get_build(
        self.build_id,
        step_test_data=lambda: self.api.m.json.test_api.output_stream(
            {'build': {'result': 'SUCCESS', 'url': 'buildbot.dummy.url/job/12'}}
        ))
    return (result.stdout['build']['result'] == 'SUCCESS',
            result.stdout['build']['url'])

  # Duplicate code from auto_bisect.bisector.get_builder_bot_for_this_platform
  def get_builder_bot_for_this_platform(self):  # pragma: no cover
    bot_name = self.api.m.properties.get('buildername', '')
    if 'win' in bot_name:
      if any(b in bot_name for b in ['x64', 'gpu']):
        return 'winx64_bisect_builder'
      return 'win_perf_bisect_builder'

    if 'android' in bot_name:
      if 'nexus9' in bot_name or 'nexus5x' in bot_name:
        return 'android_arm64_perf_bisect_builder'
      return 'android_perf_bisect_builder'

    if 'mac' in bot_name:
      return 'mac_perf_bisect_builder'

    return 'linux_perf_bisect_builder'

  def request_build(self):
    if self.api.m.chromium.c.TARGET_PLATFORM == 'android':
      self.api.m.chromium_android.clean_local_files()
    properties = {
        'parent_got_revision': self.commit_hash,
        'clobber': True,
        'build_archive_url': self.build_file_path,
    }

    deps_override = self.api.m.properties.get('deps_revision_overrides')
    if deps_override:
      properties.update({
          'deps_revision_overrides': dict(deps_override)
      })
      patch_project = self.api.m.properties.get('patch_project')
      if patch_project:
        properties.update({'patch_project': patch_project})

    if self.with_patch:
      properties_to_update = [
        'patch_gerrit_url', 'patch_issue', 'patch_project', 'patch_ref',
        'patch_repository_url', 'patch_set', 'patch_storage']
      for p in properties_to_update:
        properties.update({p: self.api.m.properties[p]})
    bot_name = self.get_builder_bot_for_this_platform()
    build_details = {
      'bucket': 'master.' + self.api.m.properties['mastername'],
      'parameters': {
        'builder_name': bot_name,
        'properties': properties
      },
      'tags':{}
    }
    self.api.m.buildbucket.use_service_account_key(
        self.api.m.puppet_service_account.get_key_path(SERVICE_ACCOUNT))
    result = self.api.m.buildbucket.put([build_details])
    self.build_id = result.stdout['results'][0]['build']['id']

  def wait_for(self): # pragma: no cover
    while True:
      if self._is_completed():
        succeeded, build_url = self._is_build_successful()
        if succeeded:
            break
        self.api.m.step.active_result.presentation.status = (
            self.api.m.step.WARNING)
        self.api.m.step.active_result.presentation.links['FAILED BUILD'] = (
            build_url)
        self.api.m.halt('Build %s patch failed' % (
            'with' if self.with_patch else 'without'))
        raise self.api.m.step.StepFailure('Build %s fails' % self.build_id)
      else:
        self.api.m.python.inline(
            'sleeping',
            """
            import sys
            import time
            time.sleep(20*60)
            sys.exit(0)
            """)

  # Adapted from auto_bisect.api.start_test_run_for_bisect
  def download_build(self, update_step, bot_db,
                     skip_download=False):
    mastername = self.api.m.properties.get('mastername')
    buildername = self.api.m.properties.get('buildername')
    if not skip_download:
      if self.api.m.chromium.c.TARGET_PLATFORM == 'android':
        # The best way to ensure the old build directory is not used is to
        # remove it.
        build_dir = self.api.m.chromium.c.build_dir.join(
            self.api.m.chromium.c.build_config_fs)
        self.api.m.file.rmtree('build directory', build_dir)

        # The way android builders on tryserver.chromium.perf are archived is
        # different from builders on chromium.perf. In order to support both
        # forms of archives, we added this temporary hack until builders are
        # fixed. See http://crbug.com/535218.
        zip_dir = self.api.m.path.join(
            self.api.m.path['checkout'], 'full-build-linux')
        if self.api.m.path.exists(zip_dir):  # pragma: no cover
          self.api.m.file.rmtree('full-build-linux directory', zip_dir)
        gs_bucket = 'gs://%s/' % self.bucket
        archive_path = self.build_file_path[len(gs_bucket):]
        self.api.m.chromium_android.download_build(
            bucket=self.bucket,
            path=archive_path)

        # The way android builders on tryserver.chromium.perf are archived is
        # different from builders on chromium.perf. In order to support both
        # forms of archives, we added this temporary hack until builders are
        # fixed. See http://crbug.com/535218.
        if self.api.m.path.exists(zip_dir):  # pragma: no cover
          self.api.m.python.inline(
              'moving full-build-linux to out/Release',
              """
              import shutil
              import sys
              shutil.move(sys.argv[1], sys.argv[2])
              """,
              args=[zip_dir, build_dir])
      else:
        self.api.m.chromium_tests.download_and_unzip_build(
            mastername, buildername, update_step, bot_db,
            build_archive_url=self.build_file_path,
            build_revision=self.commit_hash,
            override_bot_type='tester')
