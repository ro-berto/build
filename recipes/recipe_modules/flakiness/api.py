# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import collections
import copy
import inspect
import json
import random
import re

from google.protobuf import timestamp_pb2
from recipe_engine import recipe_api
from RECIPE_MODULES.build.chromium_tests import steps
from PB.go.chromium.org.luci.buildbucket.proto \
    import builds_service as builds_service_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 import common as common_rdb_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 import predicate as predicate_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)
from PB.recipe_engine import result as result_pb2

# A regular expression for file paths indicating that change in the matched file
# might introduce new tests.
# TODO(crbug.com/1204163): Extend for new tests from DEPS and build file changes
# with '^(.+(BUILD\.gn|DEPS|\.gni)|src/chromeos/CHROMEOS_LKGM|.+[T|t]est.*)$'.
_FILE_PATH_ADDING_TESTS_PATTERN = '^.+[T|t]est.*$'

# Internal labels used when we need to trim test sets at different steps.
_FINAL_TRIM = 'final'
_CROSS_REFERENCE_TRIM = 'cross reference'

# This is a hard coded test suite name list to opt out from Flake Endorser
# logic. Current names in list are these failing at test filter and repeat
# arguments.
# TODO(crbug.com/1325017): Use test configuration instead of this list.
_EXCLUDED_TEST_SUITE_NAMES = [
    'chromedriver_py_tests',
    'rendering_representative_perf_tests',
    'telemetry_desktop_minidump_unittests',
]


class TestDefinition():
  """A class to contain ResultDB TestReuslt Proto information.

  Test ID, variant hash (see go/resultdb-concepts) and whether the test comes
  from an experimental suite distinguish a |TestDefinition|. This is achieved by
  overriding __eq__ and __hash__ methods.

  Attributes:
    * duration_milliseconds: (int) Test duration in milliseconds.
    * is_experimental: (bool) Whether the test is from an experimental suite.
    * tags: (list) Tags in the ResultDB test result. If tags are provided, and
            experimental is not True, the suffix 'experimental' is searched for
            in the tags to determine whether it was an experimental run.
    * test_id: (str) ResultDB's test_id (go/resultdb-concepts)
    * test_object: (steps.Test or steps.ExperimentalTest) The test object where
                   this test comes from.
    * variants: (dict) ResultDB's variant (go/resultdb-concepts)
    * variant_hash: (str) ResultDB's variant_hash (go/resultdb-concepts)
  """

  def __init__(self,
               test_id,
               test_name=None,
               duration_milliseconds=None,
               is_experimental=False,
               tags=None,
               test_object=None,
               variants=None,
               variant_hash=None):
    """
    Args:
      * test_id: (str) ResultDB test id
      * test_name: (str) Test name to input to test suites.
      * duration_milliseconds: (int) Test duration in milliseconds.
      * is_experimental: (bool) Flag indicating whether test run was
        experimental. If tags are defined, and this is False, step_name is
        searched for in the tags to determine whether 'experimental)' suffix
        is present.
      * tags: (list) tags from ResultDB's TestResult. Used to determine whether
        the given run was experimental.
      * test_object: (steps.Test or steps.ExperimentalTest) The test object
        where this test comes from.
      * variants: either ResultDB's TestResult (dict) or a JSON string of
        key value variant definitions. The JSON string is parsed s.t. all key,
        value entries are flattened.
        (eg/ [{
          "key": "os",
          "value": "Mac-11.0"
        }]) is flattened to -> {"os": "Mac-11.0"}
      * variant_hash: (str) ResultDB's variant hash
    """
    self.test_id = test_id
    self.test_name = test_name
    self.duration_milliseconds = duration_milliseconds
    self.variants = variants
    if variants and isinstance(variants, str):
      self.variants = self._parse_string_variants(variants)
    elif hasattr(variants, 'def'):
      self.variants = getattr(variants, 'def', {})

    self.variant_hash = variant_hash

    self.is_experimental = (
        is_experimental or self._set_experimental_from_tags(tags))

    self.test_object = test_object

  def _parse_string_variants(self, variants):
    fin = {}
    j = json.loads(variants)
    for kv in j:
      fin[kv['key']] = kv['value']
    return fin

  def _set_experimental_from_tags(self, tags):
    if tags:
      for tag in tags:
        # "experimental" is the last part of step suffix (wrapped in brackets)
        # which is part of the step name. (https://bit.ly/3I4Enc6)
        if tag.key and tag.key == 'step_name' and 'experimental)' in tag.value:
          return True
    return False

  def __eq__(self, t2):
    return (self.test_id, self.variant_hash, self.is_experimental) == t2

  def __hash__(self):
    return hash((self.test_id, self.variant_hash, self.is_experimental))


class FlakinessApi(recipe_api.RecipeApi):
  """A module for new test identification on try builds."""

  def __init__(self, properties, *args, **kwargs):
    super(FlakinessApi, self).__init__(*args, **kwargs)
    self._check_for_flakiness = properties.check_for_flakiness
    # Input to cross reference step in "verify_new_tests" might be too large
    # and cause step failure, when there are too many new tests to verify
    # (caused by stale history JSON file, or a config roll adding new test
    # targets or variant configs just landed). This constant limits the number
    # of test variants passed to GetTestResultHistory RPC. The number is chosen
    # because it's about the max possible number of test variants naturally
    # added in a builder before a new test history JSON is generated.
    # Context: crbug.com/1294973
    self._max_test_variants_to_cross_reference = 1000
    # This is to limit the final new test variants that's endorsed.
    self._max_test_targets = properties.max_test_targets or 40
    self._repeat_count = properties.repeat_count or 20
    # The module will shard test reruns for swarming tests so that test
    # in each shard is shorter than this length.
    self._MAX_SHARD_TIME_MINUTES = 20
    # The max limit of test results in a test obejct, so that all results are
    # fetched for current build. If result count is larger, only unexpected
    # results are fetched. This means new tests in large suites are not
    # identified, e.g. blink_web_test.
    self.PER_TEST_OBJECT_RESULT_LIMIT = 50000
    self.COMMIT_FOOTER_KEY = 'Validate-Test-Flakiness'
    self.IDENTIFY_STEP_NAME = 'searching_for_new_tests'
    self.RUN_TEST_STEP_NAME = 'test new tests for flakiness'
    self.CALCULATE_FLAKE_RATE_STEP_NAME = 'calculate flake rates'

    self.build_count = properties.build_count or 100
    self.historical_query_count = properties.historical_query_count or 1000
    self.current_query_count = properties.current_query_count or 10000

  @property
  def test_suffix(self):
    return self._suffix_by_shard_index(0)

  @property
  def check_for_flakiness(self):
    """Boolean to determine whether flakiness logic should be run for trybots.

    This needs to be enabled in order for the coordinating function of
    this module to execute.

    Returns:
        A boolean of whether the build is identifying new tests.
    """
    return self._check_for_flakiness

  @property
  def gs_bucket(self):
    return 'flake_endorser'

  def _suffix_by_shard_index(self, index):
    """Suffix used for the input shard index when step.Test is sharded."""
    return 'check flakiness shard #%d' % index

  def gs_source_template(self, experimental=False):
    """Provides template for generator recipe

    Project, bucket and builder information are queried for in Buildbucket,
    and this provides the template used.

    Expected gs_source format:
    * {project}/{bucket}/{builder}/{build_number}

    Args:
      * experimental: (bool) flag for experimental runs, appends experimental
        to the path.

    Return:
      * (str) template
    """
    base = '{}/{}/{}/{}/'
    if experimental:
      base = 'experimental/' + base
    return base

  def builder_gs_path(self, builder, build_number=None, experimental=False):
    """Generates the GS source

    Args:
      * builder: Buildbucket's BuilderID.
      * builder_name: (str) optional arg for setting builder_name. this defaults
        to 'builder' from builder_id.
      * build_number: (int) build number to append to gs_path. defaults to
        'latest' if not set.
      * experimental: (bool) will append prefix path 'experimental/' if True.
    """
    # a list of builder names are queried for by the pre-computing builder, and
    # requires a mechanism to set this value for the correct upload path.
    return self.gs_source_template(experimental=experimental).format(
        builder.project,
        builder.bucket,
        builder.builder,
        str(build_number) if build_number else 'latest',
    ) + '{}.json.tar.gz'.format(builder.builder)

  def is_test_file_present(self, affected_files=None):
    """Checks the list of affected files and ensures there's a test file.

    This is used to determine whether the flakiness workflow should run.

    Args:
      * affected_files: (list) of files associated with the given change. see
                        self.m.chromium_checkout.get_files_affected_by_patch.

    Returns:
      (bool) whether a test file is present.
    """
    affected_files = (
        affected_files or
        self.m.chromium_checkout.get_files_affected_by_patch())
    pattern = re.compile(_FILE_PATH_ADDING_TESTS_PATTERN)
    return any(pattern.match(file_path) for file_path in affected_files)

  def get_invocations_from_change(self, change=None, step_name=None):
    """Gets ResultDB Invocation names from the same CL as the given change.

    An invocation represents a container of results, in this case from a
    buildbucket build. Invocation names can be used to map the buildbucket build
    to the ResultDB test results.

    Multiple builds can be triggered from the same CL and different patch sets.
    This method searches through all patch sets for the current build,
    gathers a list of the builds associated, and extracts the Invocation names
    from each build.

    Args:
      change (common_pb2.GerritChange): The gerrit change associated with the
        CL we want to find all invocations for. Every patch set up until and
        including the current patch set of the given change will be used to
        search buildbucket.
      step_name (string): use to override default step name.

    Returns:
        A set of ResultDB Invocation names as strings.
    """
    change = change or self.m.buildbucket.build.input.gerrit_changes[0]
    step_name = (
        step_name or 'fetching associated builds with current gerrit patchset')

    # Creating BuildPredicate object for each patch set within a CL and
    # compiling them into a list. This is to search for builds from the
    # same CL but from different patch sets to exclude from our historical
    # data, ensuring all tests new to the CL are detected as new.
    predicates = []
    for i in range(1, change.patchset + 1):
      predicates.append(
          builds_service_pb2.BuildPredicate(
              builder=self.m.buildbucket.build.builder,
              gerrit_changes=[
                  common_pb2.GerritChange(
                      host=change.host,
                      project=change.project,
                      change=change.change,
                      patchset=i),
              ]))

    search_results = self.m.buildbucket.search(
        predicate=predicates,
        report_build=False,
        step_name=step_name,
        fields=['infra.resultdb.invocation'],
    )

    inv_set = set(
        # These invocation names will later be used to query ResultDB, which
        # explicitly requires strings
        str(build.infra.resultdb.invocation) for build in search_results)

    return inv_set

  def fetch_all_related_invocations(self):
    """Gets all builds associated with the current CL, or chained CLs.

    This method searches buildbucket for all builds associated with the CL of
    the current build, or any CLs chained to the CL of the current build. Gerrit
    is used to find all chained CLs, and then each patch set of those CLs is
    used to query buildbucket for any associated builds. It then returns the
    invocation names of all of these builds and tasks within the builds.

    An invocation represents a container of results, in this case from a
    buildbucket build. Invocation names can be used to map the buildbucket build
    to the ResultDB test results.

    Returns:
        A set of invocation names as strings.
    """
    gerrit_change = self.m.buildbucket.build.input.gerrit_changes[0]
    related = self.m.gerrit.get_related_changes('https://' + gerrit_change.host,
                                                gerrit_change.change)

    change_set = {gerrit_change.change}
    excluded_invs = self.get_invocations_from_change()

    def _get_excluded_changes(excluded_invs, current_change, step):
      excluded_invs.update(
          self.get_invocations_from_change(
              change=current_change, step_name=step))

    futures = []
    for rel_change in related["changes"]:
      change_number = int(rel_change['_change_number'])
      if change_number not in change_set:
        current_change = common_pb2.GerritChange(
            host=gerrit_change.host,
            project=gerrit_change.project,
            change=change_number,
            patchset=int(rel_change['_current_revision_number']))
        step = ('fetching associated builds related with change %s' %
                str(change_number))
        futures.append(
            self.m.futures.spawn(
                _get_excluded_changes,
                excluded_invs,
                current_change,
                step,
            ))
    for f in futures:
      f.result()

    def find_sub_invocations(api, build_inv, sub_invs):
      sub_invs.extend([
          str(inv) for inv in api.resultdb.get_included_invocations(build_inv)
      ])

    # Find all task invocations of each build invocation and add these to
    # excluded.
    sub_invs = []
    futures = []
    for build_inv in excluded_invs:
      futures.append(
          self.m.futures.spawn(
              find_sub_invocations,
              self.m,
              build_inv,
              sub_invs,
          ))

    for f in futures:
      f.result()

    excluded_invs.update(sub_invs)
    return excluded_invs

  def fetch_precomputed_test_data(self):
    """Fetch the precomputed JSON file from GS

    Returns:
      dict JSON file of precomputed data
    """
    builder = self.m.buildbucket.build.builder
    source = self.builder_gs_path(
        builder, experimental=self.m.runtime.is_experimental)
    local_dest = self.m.path.mkstemp()
    self.m.gsutil.download(self.gs_bucket, source, local_dest)

    # The output dir must not exist for untar.
    output_dir = self.m.path['cleanup'].join('flake_endorser')
    self.m.tar.untar('unpack {}'.format(source), local_dest, output_dir)

    return self.m.file.read_json(
        'process precomputed test history',
        output_dir.join(builder.project, builder.bucket,
                        '{}.json'.format(builder.builder)),
        test_data=[{
            'test_id':
                ('ninja://ios/chrome/test/earl_grey2:ios_chrome_bookmarks_'
                 'eg2tests_module/TestSuite.test_a'),
            'is_experimental': False,
            'variant':
                ('[{"key":"builder","value":"ios-simulator-full-configs"},'
                 '{"key":"os","value":"Ubuntu-14.04"},{"key":"test_suite",'
                 '"value":"ios_chrome_bookmarks_eg2tests_module_iPhone 11 '
                 '14.4"}]'),
            'variant_hash': 'some_hash',
            'invocation': ['invocation/2', 'invocations/3'],
        }],
        # We turn off logging for the JSON as some of the files are pretty
        # large, and logging significantly affects the runtime in these cases.
        include_log=False)

  def process_precomputed_test_data(self, test_data, excluded_invs):
    """Process the precomputed test data into TestDefinition objects.

    Args:
      * test_data: (dict) JSON of the test data. Supported keys in the test
        data JSON include:
        - test_id: (str, required) ResultDB's test_id.
        - invocation: (list) a list of strings, which are invocations, which
          must start with 'invocations/'. See "Invocation message" at
          go/resultdb-concepts
        - variant: (str) ResultDB's variants, in JSON string.
        - variant_hash: (str) ResultDB's variant_hash, a hash of the variants.
        - is_experimental: (bool) Flag determining whether the given run was
          experimental, usually determined by the suffix `experimental` found
          from ResultDB's tags, where the tag key is step_name.
      * excluded_invs: (set) of str invocations. used to exclude test entries.

    Returns:
      set of TestDefinition objects
    """
    tests = set()
    for test_entry in test_data:
      test_invs = set(test_entry.get('invocation', []))
      # A test purely from excluded_invs is not regarded as part of history
      # tests, because it only appeared in related try job runs
      # (excluded_invs) from the same CL or chained CL
      if excluded_invs.issuperset(test_invs):
        continue

      tests.add(
          TestDefinition(
              test_entry['test_id'],
              is_experimental=test_entry.get('is_experimental', False),
              variants=test_entry.get('variant', None),
              variant_hash=test_entry.get('variant_hash', None)))
    return tests

  def verify_new_tests(self,
                       prelim_tests,
                       excluded_invs,
                       builder,
                       page_size=10000):
    """Verify the newly identified tests are new by cross-checking ResultDB.

    Queries ResultDB for the instances of the given test_ids on the builder for
    the past hours and iterates through response to eliminate any false
    positives from the preliminary new test list.

    Args:
      prelim_tests (set of TestDefinition objects): the set of TestDefinition
        objects identified as potential new tests to be cross-referenced
        with ResultDB. This set will be modified by this method to contain only
        tests not found in ResultDB existing tests.
      excluded_invs (set of str): the invocation names belonging to builds
        associated with the current build to be excluded from existing tests.
      builder (str): The name of the builder to query test results for.
      page_size (int): The number of results to return from the ResultDB search.
        Defaults to 10,000, meaning the search will return a maximum of 10,000
        test results.

    Returns:
      A set of TestDefinition objects.

    """

    def _ensure_new(time_search_range):
      results = self.m.resultdb.get_test_result_history(
          realm=self.m.buildbucket.builder_realm,
          test_id_regexp='|'.join(
              sorted(set(t.test_id for t in list(prelim_tests)))),
          variant_predicate=predicate_pb2.VariantPredicate(
              contains={'def': {
                  'builder': builder
              }}),
          time_range=time_search_range,
          page_size=page_size,
          step_name='cross reference newly identified tests against ResultDB')

      for entry in results.entries:
        test = TestDefinition(
            entry.result.test_id,
            tags=entry.result.tags,
            variants=entry.result.variant,
            variant_hash=entry.result.variant_hash,
        )
        excluded = entry.result.name.split("/tests")[0] in excluded_invs
        if test in prelim_tests and not excluded:
          prelim_tests.remove(test)

    # Time range is set as past 3 hours, to cover the gap of test history JSON
    # generation (1 hour), plus a 2 hour buffer for generate builder runtime.

    # TODO(crbug/1313712) - Timestamps in ResultDB and the way they're set up
    # in Spanner are not first class citizens for the GetTestResultHistory RPC
    # call. Providing a large time range in a single query can result in slow
    # performance, so we break down the call from a single 3 hour time range
    # into 3 separate calls, searching for an hour time range. There are some
    # caches in place from ResultDB's side to quicken this, but for cold hits
    # calls still may take up to 1 min. This is still much quicker than the 9
    # min timeouts that were being hit prior.
    now = int(self.m.time.time())
    time_offset = 3

    futures = []
    while time_offset > 0:
      earliest_time = now - 3600 * time_offset
      next_offset = time_offset - 1
      latest_time = now - 3600 * next_offset
      search_range = common_rdb_pb2.TimeRange(
          earliest=timestamp_pb2.Timestamp(seconds=earliest_time),
          latest=timestamp_pb2.Timestamp(seconds=latest_time))
      futures.append(self.m.futures.spawn(_ensure_new, search_range))
      time_offset = next_offset

    for f in futures:
      f.result()

    return prelim_tests

  def maybe_trim_new_tests(self, new_tests, trim_step_label):
    assert trim_step_label in [_FINAL_TRIM, _CROSS_REFERENCE_TRIM]
    limit = (
        self._max_test_targets if trim_step_label == _FINAL_TRIM else
        self._max_test_variants_to_cross_reference)

    if new_tests and len(new_tests) > limit:
      # There are more new tests detected than what we're permitting, so we're
      # taking a random subset for the specific step.
      res = random.sample(new_tests, limit)
      s = self.m.step('subset of new tests (%s)' % trim_step_label, cmd=None)
      s.presentation.step_text = (
          'the total number of new tests at "{}" step exceed what we permit {},'
          ' so a random subset of those tests have been selected.'.format(
              trim_step_label, self._max_test_targets))
      s.presentation.logs['new_test_subset(%s)' % trim_step_label] = '\n'.join([
          'test_id: {}, variant_hash: {}'.format(t.test_id, t.variant_hash)
          for t in res
      ])
      return res

    return new_tests

  def identify_new_tests(self, test_objects):
    """Coordinating method for identifying new tests on the current build.

    This method queries ResultDB for the historical tests run on the specified
    most recent builds on the current builder. This test list is compared with
    the tests running on the current build to identify and return new tests
    from the current CL.

    Args:
        test_objects (list): List of step.Test objects with RDB results for
          current build.

    Returns:
        A set of TestDefinition objects.
    """
    def join_tests(test_set):
      """Joins set of test_id, variant hash tuples into strings.

      For step presentations, test tuple sets cannot be logged so it is
      necessary and preferred to convert to lists of sorted concatenated
      strings.
      """
      return sorted([
          '_'.join([test_result.test_id, test_result.variant_hash])
          for test_result in test_set
      ])

    if not self.check_for_flakiness:
      return set()

    with self.m.step.nest(self.IDENTIFY_STEP_NAME) as p:
      excluded_invs = self.fetch_all_related_invocations()
      p.logs["excluded_invocation_list"] = sorted(excluded_invs)
      builder_name = self.m.buildbucket.builder_name

      try:
        precomputed_json = self.fetch_precomputed_test_data()
      except recipe_api.StepFailure:
        p.step_text = ('The current try builder may not have test data '
                       'precomputed.')
        return set()
      historical_tests = self.process_precomputed_test_data(
          precomputed_json, set(excluded_invs))
      p.logs['historical_tests'] = join_tests(historical_tests)

      # For logging purpose only.
      skipped_test_suites = set([])

      current_tests = set()
      for test_object in test_objects:
        if test_object.canonical_name in _EXCLUDED_TEST_SUITE_NAMES:
          skipped_test_suites.add(test_object.canonical_name)
          continue
        rdb_suite_result = test_object.get_rdb_results('with patch')
        for individual_test in rdb_suite_result.all_tests:
          # Use 0 as duration if the info doesn't exist.
          duration_milliseconds = individual_test.duration_milliseconds or 0

          current_tests.add(
              TestDefinition(
                  individual_test.test_id,
                  test_name=individual_test.test_name,
                  duration_milliseconds=duration_milliseconds,
                  is_experimental=isinstance(test_object,
                                             steps.ExperimentalTest),
                  test_object=test_object,
                  variant_hash=rdb_suite_result.variant_hash))

      p.logs['current_build_tests'] = join_tests(current_tests)
      if skipped_test_suites:
        p.logs['skipped_test_suites'] = '\n'.join(sorted(skipped_test_suites))

      # Comparing the current build test list to the ResultDB query test list to
      # get a preliminary set of potential new tests.
      preliminary_new_tests = current_tests.difference(historical_tests)
      p.logs['preliminary_tests'] = join_tests(preliminary_new_tests)

      if not preliminary_new_tests:
        return set()

      # Trim once before verify_new_tests to avoid input too large for RDB RPC.
      preliminary_new_tests = self.maybe_trim_new_tests(preliminary_new_tests,
                                                        _CROSS_REFERENCE_TRIM)

      # Cross-referencing the potential new tests with ResultDB to ensure they
      # are not present in existing builds.
      new_tests = self.verify_new_tests(
          prelim_tests=preliminary_new_tests,
          excluded_invs=excluded_invs,
          builder=builder_name)
      p.logs['new_tests'] = ('new tests: \n\n{}'.format('\n'.join([
          'test_id: {}, variant_hash: {}, experimental: {}'.format(
              t.test_id, t.variant_hash, t.is_experimental)
          for t in self.m.py3_migration.consistent_ordering(
              new_tests, key=lambda t: (t.test_id, t.variant_hash))
      ])))

    return new_tests

  def _shard_runs(self, total_duration_milliseconds):
    """Calculates and shards endorser test runs considering test duration.

    Args:
      total_duration_milliseconds: Total duration in milliseconds for all tests
        to run once.

    Returns:
      A list of integers representing test runs in each shard.
    """
    if total_duration_milliseconds == 0:
      return [self._repeat_count]
    max_shard_time_milliseconds = self._MAX_SHARD_TIME_MINUTES * 60 * 1000
    # Max runs per shard confirming to |self._MAX_SHARD_TIME_MINUTES|. At least
    # 1 run per shard.
    runs_per_shard = int(
        max(max_shard_time_milliseconds / total_duration_milliseconds, 1))
    remaining = self._repeat_count
    shards = []
    while remaining > 0:
      shards.append(min(remaining, runs_per_shard))
      remaining = remaining - runs_per_shard
    return shards

  def find_tests_for_flakiness(self, test_objects, affected_files=None):
    """Searches for new tests in a given change

    This method coordinates the workflow for searching and identifying new
    tests. Buildbucket is queried for a historial set of runs, cross-references
    the invocations against ResultDB, excludes certain runs and determines a
    unique set of test_id + test_variant_hash. This set is compared to the tests
    run for the current try run (both with and without patch) to determine which
    tests are new.

    There are a few restrictions in place that will skip this (and thus) the
    flakiness checks:
    1) Only new tests in new test files are checked. Thus, a new test file
       must be included as part of the change.
    2) This logic will not be triggered if "check_for_flakiness" recipe_module
       property is not enabled.
    3) If 'Validate-Test-Flakiness:skip' commit footer is set, this logic will
       be skipped.

    For test variants (variant in the definition in testing/buildbot), only the
    test name is altered. In other words, these device/variant dimensions are
    not necessarily reflected in ResultDB, so we compare a tests' canonical name
    with the 'test_suite' key from ResultDB test variant definition.

    Args:
      * test_objects = list of step.Test objects
      * affected_files = a list of affected files (Paths), provided by the
                         analyze step.
    Returns:
      A mapping from test suffixes to lists of steps.Test objects.
    """
    # Check if there are endorser footers to parse
    commit_footer_values = [
        val.lower()
        for val in self.m.tryserver.get_footer(self.COMMIT_FOOTER_KEY)
    ]
    if 'skip' in commit_footer_values:
      # No action for endorsing logic
      self.m.step(
          'skipping flaky test check since commit footer '
          '\'Validate-Test-Flakiness: Skip\' was detected.',
          cmd=None)
      return []

    if not self.is_test_file_present(affected_files=affected_files):
      self.m.step('no test files were detected with this change.', cmd=None)
      return []

    new_tests = self.identify_new_tests(test_objects)
    new_tests = self.maybe_trim_new_tests(new_tests, _FINAL_TRIM)

    test_objects_by_suffix = collections.defaultdict(list)

    # This operation is O(len(test_obj) * len(new_tests)) because parsing
    # test_id is only intended for LUCI UI grouping, see
    # http://shortn/_StMScXolrz. max_test_targets will also bind the number of
    # iterations here. We loop the test objects and check all new tests to see
    # if the test_id start similarly.
    for test in test_objects:
      total_duration_milliseconds = 0
      test_filter = []
      # find whether the Test object has a matching test_id.
      for new_test in new_tests:
        if (new_test.test_object == test):
          test_filter.append(new_test.test_name)
          total_duration_milliseconds += (new_test.duration_milliseconds or 0)
      if test_filter:
        if isinstance(test, steps.AndroidJunitTest):
          # android junit need the spec's additional_args updated with the
          # repeat and filter clauses.

          # TODO: (crbug/1311721) - parameterized tests have a [0], [1] suffix
          # appended to indicate the parameter, but it won't map to a test in
          # these filters, so we escape them with backslashes for now such that
          # they don't fail.
          # ie/ org.chromium.suite.SomeTest#testMethod[0] ->
          #     org.chromium.suite.SomeTest#testMethod\[0\]
          updated_filter = []
          for test_name in test_filter:
            if re.match('.*\[\d+\]$', test_name):
              left = (
                  test_name[:test_name.rindex('[')] + "\\" +
                  test_name[test_name.rindex('['):])
              full = left[:left.rindex(']')] + "\\" + "]"
              updated_filter.append(full)
            else:
              updated_filter.append(test_name)
          additional_args = list([
              '--gtest_repeat=%s' % str(self._repeat_count),
              '--gtest_filter=%s' % str(':'.join(updated_filter)),
              '--shards=1',
          ])
          test.spec = attr.evolve(test.spec, additional_args=additional_args)
          test_objects_by_suffix[self.test_suffix].append(test)
        elif isinstance(test, steps.ScriptTest):
          script_args = list([
              '--gtest_repeat=%s' % str(self._repeat_count),
              '--gtest_filter=%s' % str(':'.join(test_filter)),
              '--shards=1',
          ])
          test.spec = attr.evolve(test.spec, script_args=script_args)
          test_objects_by_suffix[self.test_suffix].append(test)
        elif isinstance(test.spec, steps.SwarmingTestSpec):
          shards = self._shard_runs(total_duration_milliseconds)
          for index, shard_runs in enumerate(shards):
            test_copy = copy.copy(test)
            options = steps.TestOptions(
                test_filter=test_filter, repeat_count=shard_runs, retry_limit=0)
            test_copy.test_options = options
            # we don't use swarming's shard mechanism for endorser runs.
            test_copy.spec = test.spec.with_shards(1)
            test_objects_by_suffix[self._suffix_by_shard_index(index)].append(
                test_copy)
        else:
          test_copy = copy.copy(test)
          options = steps.TestOptions(
              test_filter=test_filter,
              repeat_count=self._repeat_count,
              retry_limit=0)
          test_copy.test_options = options
          test_objects_by_suffix[self.test_suffix].append(test_copy)

    return test_objects_by_suffix

  def _flakiness_summary_markdown(self, test_stats):
    """Creates a summary markdown using flakiness run results.

    Args:
      test_stats: A dictionary mapping from (test id, variant hash) tuple to
        a tuple of (test name, list of test step names with failed runs,
        count of unexpected runs, count of total runs).
        Only tests with unexpected results are included.

        E.g.
        {
          (test_id_1, variant_hash_1): ('test_name_1',
                             ['test_suite_1 (check flakiness, 0)']),
                             1,
                             20),
          (test_id_2, variant_hash_1): ('test_name_2',
                             ['test_suite_1 (check flakiness, 0)']),
                             1,
                             20),
          (test_id_3, variant_hash_2): ('test_name_3',
                             [
                               'test_suite_1 (check flakiness, 0)',
                               'test_suite_1 (check flakiness, 1)'
                             ]
                             2,
                             20
                             )
        }

    Returns:
      A list of line strs in markdown format presenting run stats of suites and
      flaky tests.
    """
    lines = []
    for test, stats in test_stats.items():
      variant_hash = test[1]
      test_name = stats[0]
      infra_steps = stats[1]
      failures = stats[2]
      total = stats[3]
      lines.append('Test: **{}**, variant hash: {}, # of failures: {}, '
                   'total # of runs: {}. See failed runs in:'.format(
                       test_name, variant_hash, failures, total))

      lines.extend(['- %s' % step for step in infra_steps])
    return lines

  def check_run_results(self, suffix_suites):
    """Calculates and presents flakiness info using test results from input.

    Args:
      suffix_suites: A mapping from test suffixes to lists of steps.Test
        objects with valid results for the suffix.

    Returns:
      A RawResult object with the status of the build and failure message if
      there are flakiness. None if no flakiness.
    """
    # In this step, flaky tests in experimental suites (test objects) are non
    # fatal, otherwise they are fatal and will fail the build.
    flaky_non_experimental_test_stats = {}
    flaky_experimental_test_stats = {}
    with self.m.step.nest(self.CALCULATE_FLAKE_RATE_STEP_NAME) as p:
      p.step_text = (
          'Tests that have exceeded the tolerated flake rate most likely '
          'indicate flakiness. See logs for details of the flaky test '
          'and the flake rate.')
      for suffix, test_objects in suffix_suites.items():
        for t in test_objects:
          flaky_test_stats = (
              flaky_experimental_test_stats if isinstance(
                  t, steps.ExperimentalTest) else
              flaky_non_experimental_test_stats)
          rdb_results = t.get_rdb_results(suffix)
          step_name = '%s (%s)' % (t.name, suffix)
          for test in rdb_results.all_tests:
            test_name = test.test_name
            # Key is a tuple of (test_id, variant_hash)
            key = (test.test_id, rdb_results.variant_hash)
            total = test.total_test_count()
            unexpected_unpassed = test.unexpected_unpassed_count()
            # Value fields are: (test name, list of suites with failures,
            # count of unexpected unpassed runs, count of all runs)
            info = flaky_test_stats.get(key, ('', [], 0, 0))
            if unexpected_unpassed > 0:
              info[1].append(step_name)
            flaky_test_stats[key] = (test_name, info[1],
                                     info[2] + unexpected_unpassed,
                                     info[3] + total)

      # Keep only test variants with unexpected results.
      test_stats_filter = lambda item: item[1][2] > 0
      flaky_non_experimental_test_stats = dict(
          filter(test_stats_filter, flaky_non_experimental_test_stats.items()))
      flaky_experimental_test_stats = dict(
          filter(test_stats_filter, flaky_experimental_test_stats.items()))

      non_experimental_summary_lines = []
      if flaky_non_experimental_test_stats:
        non_experimental_summary_lines.append(
            'Flaky new test(s) in non-experimental suites (fatal):')
        non_experimental_summary_lines.extend(
            self._flakiness_summary_markdown(flaky_non_experimental_test_stats))

      experimental_summary_lines = []
      if flaky_experimental_test_stats:
        experimental_summary_lines.append(
            'Flaky new test(s) in experimental suites (non-fatal):')
        experimental_summary_lines.extend(
            self._flakiness_summary_markdown(flaky_experimental_test_stats))

      if non_experimental_summary_lines or experimental_summary_lines:
        p.logs['flaky tests'] = ('\n'.join(non_experimental_summary_lines +
                                           experimental_summary_lines))

        if non_experimental_summary_lines:
          p.status = self.m.step.FAILURE
          summary_lines = [
              'Some new test(s) added from your CL appear '
              'to be flaky. Please check "%s" step for test identification and '
              '"%s" step for test rerun details.' %
              (self.IDENTIFY_STEP_NAME, self.RUN_TEST_STEP_NAME)
          ]
          summary_lines.extend(non_experimental_summary_lines)
          summary_markdown = '\n\n'.join(summary_lines)[:3500]
          summary_markdown += (
              '\n\nSee full logs in "flaky tests" under %s step.' %
              self.CALCULATE_FLAKE_RATE_STEP_NAME)
          return result_pb2.RawResult(
              summary_markdown=summary_markdown, status=common_pb2.FAILURE)

        # When there is non fatal flakiness, let users know why the build
        # doesn't fail.
        p.step_text += ('\nFlaky tests in logs are non fatal because they come '
                        'from experimental suites.')

    return None
