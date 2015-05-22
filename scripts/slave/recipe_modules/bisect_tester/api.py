# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os

from slave import recipe_api
from . import perf_test

BUCKET = 'chrome-perf'
RESULTS_GS_DIR = 'bisect-results'


class BisectTesterApi(recipe_api.RecipeApi):
  """A module for the bisect tester bot using the chromium recipe."""

  def __init__(self, **kwargs):
    super(BisectTesterApi, self).__init__(**kwargs)

  def load_config_from_dict(self, bisect_config):
    """Copies the required configuration keys to a new dict."""
    if bisect_config['test_type'] == 'perf':
      return {
          'test_type': 'perf',
          'command': bisect_config['command'],
          'metric': bisect_config['metric'],
          'repeat_count': int(bisect_config['repeat_count']),
          'timeout_seconds': float(bisect_config['max_time_minutes']) * 60,
          'truncate_percent': float(bisect_config['truncate_percent']),
      }
    else:  # pragma: no cover
      # TODO(robertocn): Add test to remove this pragma
      raise NotImplementedError('Test type %s not supported.' %
                                bisect_config['test_type'])

  def run_test(self, test_config):
    """Call the appropriate test function depending on the type of bisect."""
    if test_config['test_type'] == 'perf':
      return perf_test.run_perf_test(self, test_config)
    else:  # pragma: no cover
      # TODO(robertocn): Add test to remove this pragma
      raise NotImplementedError('Test type %s not supported.' %
                                test_config['test_type'])

  def digest_run_results(self, results, test_config):
    """Calculates relevant statistical functions from the results."""
    if test_config['test_type'] == 'perf':
      return perf_test.truncate_and_aggregate(self, results,
                                              test_config['truncate_percent'])
    else:  # pragma: no cover
      # TODO(robertocn): Add test to remove this pragma
      raise NotImplementedError('Test type %s not supported.' %
                                test_config['test_type'])

  def upload_results(self, output, results, retcodes):
    """Puts the results as a JSON file in a GS bucket."""
    gs_filename = (RESULTS_GS_DIR + '/' +
                   self.m.properties['job_name'] + '.results')
    contents = {'results': results, 'output': output, 'retcodes': retcodes}
    contents_json = json.dumps(contents)
    local_save_results = self.m.python('saving json to temp file',
                                       self.resource('put_temp.py'),
                                       stdout=self.m.raw_io.output(),
                                       stdin=self.m.raw_io.input(
                                           contents_json))
    local_file = local_save_results.stdout.splitlines()[0].strip()
    # TODO(robertocn): Look into using self.m.json.input(contents) instead of
    # local_file.
    self.m.gsutil.upload(local_file, BUCKET, gs_filename)

  def upload_job_url(self):
    """Puts the URL to the job's status on a GS file."""
    gs_filename = RESULTS_GS_DIR + '/' + self.m.properties['job_name']
    if 'TESTING_MASTER_HOST' in os.environ:  # pragma: no cover
      url = "http://%s:8041/json/builders/%s/builds/%s" % (
          os.environ['TESTING_MASTER_HOST'],
          self.m.properties['buildername'],
          self.m.properties['buildnumber'])
    else:
      url = "http://build.chromium.org/p/%s/json/builders/%s/builds/%s" % (
          self.m.properties['mastername'],
          self.m.properties['buildername'],
          self.m.properties['buildnumber'])
    local_save_results = self.m.python('saving url to temp file',
                                       self.resource('put_temp.py'),
                                       stdout=self.m.raw_io.output(),
                                       stdin=self.m.raw_io.input(url))
    local_file = local_save_results.stdout.splitlines()[0].strip()
    self.m.gsutil.upload(local_file, BUCKET, gs_filename, name=str(gs_filename))
