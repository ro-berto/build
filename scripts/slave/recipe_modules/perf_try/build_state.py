# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import uuid

# This is a wrapper class of revision that stores its build path and
# queries its status. Part of the code are adapted from the RevisionState
# class from auto-bisect module
class BuildState(object):

  SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION = range(5)

  def __init__(self, api, commit_hash, with_patch):
    super(BuildState, self).__init__()
    self.api = api
    self.commit_hash = str(commit_hash)
    if api.m.properties.get('is_test'):
      self._patch_hash = with_patch * '123456'
    else:
      self._patch_hash =  with_patch * str(uuid.uuid4()) # pragma: no cover
    self.build_id = None
    if with_patch:
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
      if 'nexus9' in bot_name:
        return 'gs://%s/android_perf_rel_arm64/full-build-linux_' % self.bucket
      return 'gs://%s/android_perf_rel/full-build-linux_' % self.bucket
    if 'mac' in bot_name:
      return 'gs://%s/Mac Builder/full-build-mac_' % self.bucket
    return 'gs://%s/Linux Builder/full-build-linux' % self.bucket

  def is_completed(self):
    result = self.api.m.buildbucket.get_build(self.build_id)
    return result.stdout['status'] == 'COMPLETED'

  def is_build_archived(self): # pragma: no cover
    result = self.api.m.buildbucket.get_build(self.build_id)
    return result.stdout['result'] == 'SUCCESS'
