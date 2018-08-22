# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import base64
import math

from collections import defaultdict

from recipe_engine import recipe_test_api

from . import revision_state


class AutoBisectStagingTestApi(recipe_test_api.RecipeTestApi):
  def buildbot_job_status_mock(self, bb_data_list):
    if bb_data_list:
      return bb_data_list.pop()
    return self.m.json.output_stream(
        {'build': {
            'result': 'SUCCESS',
            'status': 'COMPLETED'}})

  def compare_samples_data(self, data, rev_a, rev_b):
    """Produce a mock result from compare_samples.

    A value of 1 indicates pre-regression,
    A value of 7 indicates post-regression,
    Neither, need more data.
    A value of 404 forces NEED_MORE_DATA regardless
    """

    values_a = data[rev_a.commit_hash][:rev_a.test_run_count]
    values_b = data[rev_b.commit_hash][:rev_b.test_run_count]

    result = revision_state.FAIL_TO_REJECT
    if (rev_a.test_run_count < 15 and rev_b.test_run_count < 15) or (
        404 in values_a + values_b):
      result = revision_state.NEED_MORE_DATA
    elif ((1 in values_a and 7 in values_b) or
          (7 in values_a and 1 in values_b)):
      result = revision_state.REJECT

    return self.m.json.output_stream(
        {
            'sampleA': values_a,
            'sampleB': values_b,
            'result': {
                'U': 123,
                'p': 0.001,
                'significance': result
            }
        })

  @recipe_test_api.mod_test_data
  def hash_cp_map(self, items):
    result = {}
    for item in items:
      if 'commit_pos' in item:
        result[item['commit_pos']] = self.m.json.output_stream(
            {'git_sha': item['hash']})
    return result

  @recipe_test_api.mod_test_data
  @staticmethod
  def parsed_values(items):
    return {i['hash']: i.get('parsed_values', []) for i in items}

  @recipe_test_api.mod_test_data
  def revision_list(self, items):
    result = {}
    for item in items:
      depot = item.get('depot', 'chromium')
      result.setdefault(depot, [])
      result[depot].append([item['hash'], item.get('commit_pos')])
    # Exclude the start of the revision range.
    if 'chromium' in result:
      result['chromium'] = result['chromium'][1:]
    for depot in result:
      result[depot] = self.m.json.output_stream(result[depot])
    return result

  @recipe_test_api.mod_test_data
  def revision_list_internal(self, items):
    result = {}
    for item in items:
      depot = item.get('depot', 'chromium')
      result.setdefault(depot, [])
      result[depot].append([item['hash'], item.get('commit_pos')])
    for depot in result:
      r = {
              'log': [{
                  'commit': i[0],
                  'message': i[1],
               } for i in result[depot]]
      }
      result[depot] = self.m.json.output(r)
    return result

  @recipe_test_api.mod_test_data
  def deps_change(self, items):
    # If the revision has the key DEPS_change, we mock the result of git show to
    # appear as if DEPS was among the files changed by the CL.
    result = {}
    for item in items:
      git_output = ''
      if 'DEPS_change' in item:
          git_output = 'DEPS'
      result[item['hash']] = self.m.raw_io.stream_output(git_output)
    return result

  @recipe_test_api.mod_test_data
  def diff_patch(self):
    return self.m.raw_io.stream_output("""
diff --git a/DEPS b/DEPS
index 029be3b..2b3ea0a 100644
--- a/DEPS
+++ b/DEPS
@@ -13,7 +13,7 @@ deps = {
     '@98fc59a5896f4ea990a4d527548204fed8f06c64',
   'build/third_party/infra_libs':
     'https://chromium.googlesource.com/infra/infra/packages/infra_libs.git'
-    '@a13e6745a4edd01fee683e4157ea0195872e64eb',
+    '@15ea0920b5f83d0aff4bd042e95bc388d069d51c',
   'build/third_party/lighttpd':
     'https://chromium.googlesource.com/chromium/deps/lighttpd.git'
     '@9dfa55d15937a688a92cbf2b7a8621b0927d06eb',
    """)

  @recipe_test_api.mod_test_data
  def download_deps(self, items):
    result = {}
    for item in items:
      deps_content = ''
      if 'DEPS' in item:
        deps_content = item['DEPS']
        r = {'value': base64.b64encode(deps_content)}
        result[item['hash']] = self.m.json.output_stream(r)
    return result

  @recipe_test_api.mod_test_data
  def deps(self, items):
    result = {}
    for item in items:
      deps_content = ''
      if 'DEPS' in item:
        deps_content = item['DEPS']
      result[item['hash']] = self.m.raw_io.stream_output(deps_content)
    return result

  def _exists_result(self, exists=True):
    if exists:
      return  self.m.raw_io.stream_output('GS location exists', retcode=0)
    return  self.m.raw_io.stream_output('GS location does not exist', retcode=1)

  @recipe_test_api.mod_test_data
  def gsutil_exists(self, items):
    result = {}
    for item in items:
      if 'gsutil_exists' in item:
        result[item['hash']] = [
            self._exists_result(i) for i in item['gsutil_exists']]
    return result

  @recipe_test_api.mod_test_data
  def run_results(self, items):
    def single_result(v):
      data = v.get('stdout', 'text from actual benchmark, (ignored)')
      retcode = v.get('retcode', 0)
      return (self.m.raw_io.stream_output(data=data, retcode=retcode) +
              self.m.raw_io.output_text(data=data))

    result = {'default': self.m.raw_io.stream_output('mock output', retcode=0)}
    for item in items:
      if 'test_results' in item:
        result[item['hash']] = [single_result(v) for v in item['test_results']]
    return result

  @recipe_test_api.mod_test_data
  def cl_info(self, items):
    result = {}
    for item in items:
      result[item['hash']] = self.m.json.output_stream(
          item.get('cl_info', {}))
    return result

  @recipe_test_api.mod_test_data
  def build_status(self, items):
    result = {}
    for item in items:
      if 'build_status' in item:
        result[item['hash']] = []
        for entry in item['build_status']:
          if isinstance(entry, dict):
            result[item['hash']].append(self.m.json.output_stream(entry))
          else:
            result[item['hash']].append(
                self.m.json.output(entry, retcode=1) +
                self.m.json.output_stream(entry, retcode=1))
    return result

  def __call__(self, config_items):
    return (
        self.parsed_values(config_items)
        + self.hash_cp_map(config_items)
        + self.revision_list(config_items)
        + self.revision_list_internal(config_items)
        + self.run_results(config_items)
        + self.deps_change(config_items)
        + self.deps(config_items)
        + self.download_deps(config_items)
        + self.cl_info (config_items)
        + self.diff_patch()
        + self.gsutil_exists(config_items)
        + self.build_status(config_items)
    )
