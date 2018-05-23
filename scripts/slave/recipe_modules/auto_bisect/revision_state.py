# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""An interface for holding state and result of revisions in a bisect job.

When implementing support for tests other than perf, one should extend this
class so that the bisect module and recipe can use it.

See perf_revision_state for an example.
"""

import collections
import hashlib
import json
import math
import os
import tempfile
import re

from recipe_engine.recipe_api import StepFailure

from . import depot_config
from . import bisect_exceptions

# These relate to how to increase the number of repetitions during re-test
MINIMUM_SAMPLE_SIZE = 6
INCREASE_FACTOR = 1.5
# If after testing a revision this many times it cannot be classified, fail.
MAX_TESTS_PER_REVISION = 20

NOT_SIGNIFICANTLY_DIFFERENT = 'NOT_SIGNIFICANTLY_DIFFERENT'
SIGNIFICANTLY_DIFFERENT = 'SIGNIFICANTLY_DIFFERENT'
NEED_MORE_DATA = 'NEED_MORE_DATA'
REJECT = 'REJECT'
FAIL_TO_REJECT = 'FAIL_TO_REJECT'

class RevisionState(object):
  """Abstracts the state of a single revision on a bisect job."""

  def __init__(self, bisector, commit_hash, depot_name=None,
               base_revision=None):
    """Creates a new instance to track the state of a revision.

    Args:
      bisector (Bisector): The object performing the bisection.
      commit_hash (str): The hash identifying the revision to represent.
      depot_name (str): The name of the depot as specified in DEPS. Must be a
        key in depot_config.DEPOT_DEPS_NAME .
      base_revision (RevisionState): The revision state to patch with the deps
        change.
    """
    super(RevisionState, self).__init__()
    self.bisector = bisector
    self._good = None
    self._built = False
    self._failed_build = None
    self.failed = False
    self.deps = None
    self.test_results_url = None
    self.build_archived = False
    self.next_revision = None
    self.previous_revision = None
    self.job_name = None
    self.patch_file = None
    self.deps_revision = None
    self.depot_name = depot_name or self.bisector.base_depot
    self.depot = depot_config.DEPOT_DEPS_NAME[self.depot_name]
    self.commit_hash = str(commit_hash)
    self._rev_str = None
    self.base_revision = base_revision
    self.top_revision = self
    # The difference between revsion overrides and revsion ladder is that the
    # former is indexed by paths, e.g. 'src/third_party/skia' and the latter is
    # indexed by depot name, e.g. 'skia'.
    self.revision_overrides = {}
    self.revision_ladder = {self.depot_name: self.commit_hash}
    self.build_id = None
    if self.base_revision:
      self.needs_patch = True
      self.revision_overrides[self.depot['src']] = self.commit_hash
      # To allow multiple nested levels, we go to the topmost revision.
      while self.top_revision.base_revision:
        self.top_revision = self.top_revision.base_revision
        # We want to carry over any overrides from the base revision(s) without
        # overwriting any overrides specified at the self level.
        self.revision_ladder[self.top_revision.depot_name] = (
            self.top_revision.commit_hash)
        self.revision_overrides = dict(
            self.top_revision.revision_overrides.items() +
            self.revision_overrides.items())
      self.deps_sha = hashlib.sha1(self.revision_string()).hexdigest()
      self.deps = dict(base_revision.deps)
      self.deps[self.depot_name] = self.commit_hash
    else:
      self.needs_patch = False
    self.build_url = self.bisector.get_platform_gs_prefix() + self._gs_suffix()
    self.valueset_paths = []
    self.chartjson_paths = []
    self.buildbot_paths = []
    self.debug_values = []
    self.return_codes = []
    self._test_config = None
    self.failure_reason = None

    if self.bisector.test_type == 'perf':
      self.repeat_count = MINIMUM_SAMPLE_SIZE
    else:
      self.repeat_count = self.bisector.bisect_config.get(
          'repeat_count', MINIMUM_SAMPLE_SIZE)

  @property
  def good(self):
    return self._good == True

  @property
  def bad(self):
    return self._good == False

  @good.setter
  def good(self, value):
    self._good = value

  @bad.setter
  def bad(self, value):
    self._good = not value

  @property
  def test_run_count(self):
    return max(
        len(self.valueset_paths),
        len(self.chartjson_paths),
        len(self.buildbot_paths),
        len(self.return_codes))

  @property
  def display_values(self):
    if self.bisector.is_return_code_mode():
      return self.return_codes
    return self.debug_values

  @property
  def mean(self):
    if self.debug_values:
      return float(sum(self.debug_values))/len(self.debug_values)

  @property
  def std_dev(self):
    if self.debug_values:
      mn = self.mean
      numer = sum(pow(x - mn, 2) for x in self.debug_values)
      # Sample standard deviation
      N = float(max(1, len(self.debug_values) - 1))
      return math.sqrt(numer / N)

  def _check_values_produced(self):
    """Checks if any values were output from tests."""
    api = self.bisector.api
    if api._test_data.enabled:
      return api._test_data.get('parsed_values', {}).get(self.commit_hash)
    return (  # pragma: no cover
        self.chartjson_paths or self.valueset_paths or self.buildbot_paths)

  def start_job(self):
    api = self.bisector.api
    try:
      if not self._is_build_archived():
        self._request_build()
        with api.m.step.nest('Waiting for build'):
          while not self._is_build_archived():
            api.m.python.inline(
                'sleeping',
                """
                import sys
                import time
                time.sleep(5*60)
                sys.exit(0)
                """)
            if self.is_build_failed():
              self.failed = True
              self.failure_reason = (
                  'Failed to compile revision %s. Buildbucket job id %s' % (
                      self.revision_string(), self.build_id))
              return

      # Individual tests failing don't need to break the entire bisect run.
      try:
        self._do_test()
        # TODO(robertocn): Add a test to remove this CL
        while not self._check_revision_good():  # pragma: no cover
          min(self, self.bisector.lkgr, self.bisector.fkbr,
              key=lambda(x): x.test_run_count)._do_test()
      except StepFailure as e:  # pragma: no cover
        raise bisect_exceptions.UntestableRevisionException(e.reason)

      # If this is the initial good/bad revision, we should to check if any
      # values are even produced and fail if they aren't. This allows the
      # "Gathering Reference Values" step to fail instead of some unrelated
      # future step.
      if not self.bisector.is_return_code_mode():
        if (self in [self.bisector.good_rev, self.bisector.bad_rev] and not
            self._check_values_produced()):
          self.failed = True
          self.failure_reason = 'Test runs failed to produce output.'

    except bisect_exceptions.UntestableRevisionException as e:
      self.failure_reason = e.message
      self.failed = True


  def deps_change(self):
    """Uses `git show` to see if a given commit contains a DEPS change."""
    api = self.bisector.api
    working_dir = api.working_dir
    cwd = working_dir.join(
        depot_config.DEPOT_DEPS_NAME[self.depot_name]['src'])
    name = 'Checking DEPS for ' + self.commit_hash
    with api.m.context(cwd=cwd):
      step_result = api.m.git(
          'show', '--name-only', '--pretty=format:',
          self.commit_hash, stdout=api.m.raw_io.output_text(), name=name,
          step_test_data=lambda: api._test_data['deps_change'][self.commit_hash]
      )
    if 'DEPS' in step_result.stdout.splitlines():  # pragma: no cover
      return True
    return False  # pragma: no cover

  def _gen_deps_local_scope(self):
    """Defines the Var and From functions in a dict for calling exec.

    This is needed for executing the DEPS file.
    """
    deps_data = {
        'Var': lambda _: deps_data['vars'][_],
        'From': lambda *args: None,
    }
    return deps_data

  def _read_content(self, url, file_name, branch):   # pragma: no cover
    """Uses gitiles recipe module to download and read file contents."""
    api = self.bisector.api
    try:
      return api.m.gitiles.download_file(
          repository_url=url, file_path=file_name, branch=branch,
          step_test_data=lambda: api._test_data['download_deps'].get(
              self.commit_hash, ''))
    except (TypeError, StepFailure):
      err = 'Could not read content for %s/%s/%s' % (url, file_name, branch)
      api.m.step.active_result.presentation.status = api.m.step.WARNING
      api.m.step.active_result.presentation.logs['Gitiles Warning'] = [err]
      return None

  def read_deps(self, recipe_tester_name):
    """Sets the dependencies for this revision from the contents of DEPS."""
    api = self.bisector.api
    if (self.bisector.internal_bisect and
        'deps_file' in self.depot):  # pragma: no cover
      deps_file_contents = self._read_content(
          self.depot['url'],
          self.depot['deps_file'],
          self.commit_hash)
      # On April 5th, 2016 .DEPS.git was changed to DEPS on android-chrome repo,
      # we are doing this in order to support both deps files.
      if not deps_file_contents:
        deps_file_contents = self._read_content(
            self.depot['url'],
            depot_config.DEPS_FILENAME,
            self.commit_hash)
    else:
      step_result = api.m.python(
          'fetch file %s:%s' % (self.commit_hash, depot_config.DEPS_FILENAME),
          api.resource('fetch_file.py'),
          [depot_config.DEPS_FILENAME, '--commit', self.commit_hash],
          stdout=api.m.raw_io.output_text(),
          step_test_data=lambda: api._test_data['deps'][self.commit_hash]
      )
      deps_file_contents = step_result.stdout
    try:
      deps_data = self._gen_deps_local_scope()
      exec (deps_file_contents or 'deps = {}') in {}, deps_data
      deps_data = deps_data['deps']
    except ImportError:  # pragma: no cover
      # TODO(robertocn): Implement manual parsing of DEPS when exec fails.
      raise NotImplementedError('Path not implemented to manually parse DEPS')

    revision_regex = re.compile('.git@(?P<revision>[a-fA-F0-9]+)')
    results = {}
    for depot_name, depot_data in depot_config.DEPOT_DEPS_NAME.iteritems():
      if (depot_data.get('platform') and
          depot_data.get('platform') not in recipe_tester_name.lower()):
        continue

      if (depot_data.get('recurse') and
          self.depot_name in depot_data.get('from')):
        depot_data_src = depot_data.get('src') or depot_data.get('src_old')
        src_dir = deps_data.get(depot_data_src)
        if src_dir:
          re_results = revision_regex.search(src_dir)
          if re_results:
            results[depot_name] = re_results.group('revision')
          else:  # pragma: no cover
            warning_text = ('Could not parse revision for %s while bisecting '
                            '%s' % (depot_name, self.depot))
            if warning_text not in self.bisector.warnings:
              self.bisector.warnings.append(warning_text)
        else:
          results[depot_name] = None
    self.deps = results
    return

  def _is_build_archived(self):
    """Checks if the revision is already built and archived."""
    if not self.build_archived:
      api = self.bisector.api
      data = []
      if api._test_data.enabled:
        data = (api._test_data.get('gsutil_exists', {}).get(self.commit_hash) or
                [collections.namedtuple('retcode_attr', ['retcode'])(0)])
      self.build_archived = api.gsutil_file_exists(
          self.build_url, step_test_data=data.pop)
    self._built = self.build_archived
    return self.build_archived

  def is_build_failed(self):
    if self._built:  # pragma: no cover
      return self._failed_build
    api = self.bisector.api
    api.m.buildbucket.use_service_account_key(
        api.m.puppet_service_account.get_key_path(api.SERVICE_ACCOUNT))
    try:
      result = api.m.buildbucket.get_build(
          self.build_id,
          step_test_data=lambda: api.test_api.buildbot_job_status_mock(
              api._test_data.get('build_status', {}).get(self.commit_hash, [])))
    except StepFailure:
      # If the check fails, we cannot assume that the build is failed.
      return False
    if result.stdout['build']['status'] == 'COMPLETED':
      self._built = True
      if result.stdout['build'].get('result') != 'SUCCESS':
        self._failed_build = True
        return True
    return False

  def _gs_suffix(self):
    """Provides the expected right half of the build filename.

    This takes into account whether the build has a deps patch.
    """
    name_parts = [self.top_revision.commit_hash]
    if self.needs_patch:
      name_parts.append(self.deps_sha)
    return '%s.zip' % '_'.join(name_parts)

  def _read_test_results(self, results):
    # Results will be a dictionary containing path to chartjsons, paths to
    # valueset, list of return codes.
    self.return_codes.extend(results.get('retcodes', []))
    if results.get('errors'):  # pragma: no cover
      self.failed = True
      if 'MISSING_METRIC' in results.get('errors'):
        self.bisector.surface_result('MISSING_METRIC')
      raise bisect_exceptions.UntestableRevisionException(
          'The metric was not found in the output.')
    elif self.bisector.is_return_code_mode():
      assert len(results['retcodes'])
    else:
      self.valueset_paths.extend(results.get('valueset_paths'))
      self.chartjson_paths.extend(results.get('chartjson_paths'))
      self.buildbot_paths.extend(results.get('stdout_paths'))

  def _request_build(self):
    """Posts a request to buildbot to build this revision and archive it."""
    api = self.bisector.api
    bot_name = self.bisector.get_builder_bot_for_this_platform()
    build_details = {
        'bucket': 'master.' + api.m.properties['mastername'],
        'parameters': {
            'builder_name': bot_name,
            'properties': {
                'parent_got_revision': self.top_revision.commit_hash,
                'clobber': True,
                'build_archive_url': self.build_url,
            },
        },
    }
    if self.revision_overrides:
      build_details['parameters']['properties']['deps_revision_overrides'] = \
          self.revision_overrides

    api.m.buildbucket.use_service_account_key(
        api.m.puppet_service_account.get_key_path(api.SERVICE_ACCOUNT))
    try:
      result = api.m.buildbucket.put(
          [build_details],
          step_test_data=lambda: api.m.json.test_api.output_stream(
              {'results':[{'build':{'id':'1201331270'}}]}))
    except StepFailure:  # pragma: no cover
      self.bisector.surface_result('BUILD_FAILURE')
      raise
    self.build_id = result.stdout['results'][0]['build']['id']


  def _get_bisect_config_for_tester(self):
    """Copies the key-value pairs required by a tester bot to a new dict."""
    result = {}
    required_test_properties = {
        'truncate_percent',
        'metric',
        'command',
        'test_type'
    }
    for k, v in self.bisector.bisect_config.iteritems():
      if k in required_test_properties:
        result[k] = v
    result['repeat_count'] = self.repeat_count
    self._test_config = result
    return result

  def _do_test(self):
    """Triggers tests for a revision, either locally or via try job.

    If local testing is enabled (i.e. director/tester merged) then
    the test will be run on the same machine. Otherwise, this posts
    a request to buildbot to download and perf-test this build.
    """
    if self.test_run_count:  # pragma: no cover
      self.repeat_count =  max(MINIMUM_SAMPLE_SIZE, math.ceil(
          self.test_run_count * 1.5)) - self.test_run_count

    api = self.bisector.api
    perf_test_properties = {
        'properties': {
            'revision': self.top_revision.commit_hash,
            'parent_got_revision': self.top_revision.commit_hash,
            'parent_build_archive_url': self.build_url,
            'bisect_config': self._get_bisect_config_for_tester(),
            'job_name': self.job_name,
            'revision_ladder': self.revision_ladder,
            'deps_revision_overrides': self.revision_overrides,
        },
    }
    skip_download = self.bisector.last_tested_revision == self
    self.bisector.last_tested_revision = self
    overrides = perf_test_properties['properties']

    def run_test_step_test_data():
      """Returns a single step data object when called.

      These are expected to be populated by the test_api.
      """
      if api._test_data['run_results'].get(self.commit_hash):
        return api._test_data['run_results'][self.commit_hash].pop(0)
      return api._test_data['run_results']['default']

    self._read_test_results(api.run_local_test_run(
        overrides, skip_download=skip_download,
        step_test_data=run_test_step_test_data
    ))

  def _check_revision_good(self):  # pragma: no cover
    """Determines if a revision is good or bad.

    Returns:
      True if the revision is either good or bad, False if it cannot be
      determined from the available data.
    """
    # Do not reclassify revisions. Important for reference range.
    if self.good or self.bad:
      return True

    lkgr = self.bisector.lkgr
    fkbr = self.bisector.fkbr
    if self.bisector.is_return_code_mode():
      if self.overall_return_code == lkgr.overall_return_code:
        self.good = True
      else:
        self.bad = True
      return True
    diff_from_good = self.bisector.compare_revisions(self, lkgr)
    diff_from_bad = self.bisector.compare_revisions(self, fkbr)
    if (diff_from_good == NOT_SIGNIFICANTLY_DIFFERENT and
        diff_from_bad == NOT_SIGNIFICANTLY_DIFFERENT):
      # We have reached the max number of samples and have not established
      # difference, give up.
      raise bisect_exceptions.InconclusiveBisectException()
    if (diff_from_good == SIGNIFICANTLY_DIFFERENT and
        diff_from_bad == SIGNIFICANTLY_DIFFERENT):
      # Multiple regressions.
      # For now, proceed bisecting the biggest difference of the means.
      dist_from_good = abs(self.mean - lkgr.mean)
      dist_from_bad = abs(self.mean - fkbr.mean)
      if dist_from_good > dist_from_bad:
        # TODO(robertocn): Add way to handle the secondary regression
        #self.bisector.handle_secondary_regression(self, fkbr)
        self.bad = True
        return True
      else:
        #self.bisector.handle_secondary_regression(lkgr, self)
        self.good = True
        return True
    if diff_from_good == SIGNIFICANTLY_DIFFERENT:
      self.bad = True
      return True
    elif diff_from_bad == SIGNIFICANTLY_DIFFERENT:
      self.good = True
      return True
    # NEED_MORE_DATA
    if self.test_run_count > MAX_TESTS_PER_REVISION:
      raise bisect_exceptions.UntestableRevisionException(
          'Not enough data after testing %s %d times' % (
              self.revision_string(), self.test_run_count))
    return False


  def revision_string(self):
    if self._rev_str:
      return self._rev_str
    result = ''
    if self.base_revision:  # pragma: no cover
      result += self.base_revision.revision_string() + ','
    commit = self.commit_hash[:10]
    if self.depot_name == 'chromium':
      try:
        commit = str(self.bisector.api.m.commit_position
                     .chromium_commit_position_from_hash(self.commit_hash))
      except StepFailure:
        pass # Failure to resolve a commit position is no reason to break.
    result += '%s@%s' % (self.depot_name, commit)
    self._rev_str = result
    return self._rev_str

  def __repr__(self):  # pragma: no cover
    if not self.test_run_count:
      return ('RevisionState(rev=%s), values=[]' % self.revision_string())
    if self.bisector.is_return_code_mode():
      return ('RevisionState(rev=%s, mean=%r, overall_return_code=%r, '
              'std_dev=%r)') % (self.revision_string(), self.mean,
                                self.overall_return_code, self.std_dev)
    return ('RevisionState(rev=%s, mean_value=%r, std_dev=%r)' % (
        self.revision_string(), self.mean, self.std_dev))

  @property
  def overall_return_code(self):
    if self.bisector.is_return_code_mode():
      if self.return_codes:
        if max(self.return_codes):
          return 1
        return 0
      raise ValueError('overall_return_code needs non-empty sample'
                       )  # pragma: no cover
    raise ValueError('overall_return_code only applies to return_code bisects'
                     )  # pragma: no cover
