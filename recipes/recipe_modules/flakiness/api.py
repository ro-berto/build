# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
import inspect
import random
import re

from recipe_engine import recipe_api
from RECIPE_MODULES.build.chromium_tests import steps
from PB.go.chromium.org.luci.buildbucket.proto \
    import builds_service as builds_service_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 import predicate as predicate_pb2

# A regular expression for file paths indicating that change in the matched file
# might introduce new tests.
_FILE_PATH_ADDING_TESTS_PATTERN = ('^(.+(BUILD\.gn|DEPS|\.gni)|'
                                   'src/chromeos/CHROMEOS_LKGM|.+[T|t]est.*)$')


class TestDefinition():
  """A class to contain ResultDB TestReuslt Proto information.

  Test ID, variant hash (see go/resultdb-concepts) and whether the test comes
  from an experimental suite distinguish a |TestDefinition|. This is achieved by
  overriding __eq__ and __hash__ methods.

  Attributes:
    * is_experimental: (bool) Whether the test is from an experimental suite.
    * tags: (list) Tags in the ResultDB test result
    * test_id: (string) ResultDB's test_id (go/resultdb-concepts)
    * variant_hash: (stirng) ResultDB's variant_hash (go/resultdb-concepts)
  """

  def __init__(self, test_result):
    self.tags = test_result.tags if test_result.tags else []
    self.test_id = test_result.test_id
    self.variants = getattr(test_result.variant,
                            'def') if test_result.variant else {}
    self.variant_hash = test_result.variant_hash

    self.is_experimental = False
    for tag in self.tags:
      # "experimental" is the last part of step suffix (wrapped in brackets)
      # which is part of the step name. (https://bit.ly/3I4Enc6)
      if tag.key and tag.key == 'step_name' and 'experimental)' in tag.value:
        self.is_experimental = True

  def __eq__(self, t2):
    return (self.test_id, self.variant_hash, self.is_experimental) == t2

  def __hash__(self):
    return hash((self.test_id, self.variant_hash, self.is_experimental))


class FlakinessApi(recipe_api.RecipeApi):
  """A module for new test identification on try builds."""

  def __init__(self, properties, *args, **kwargs):
    super(FlakinessApi, self).__init__(*args, **kwargs)
    self._check_for_flakiness = properties.check_for_flakiness
    self._max_test_targets = properties.max_test_targets or 40
    self._repeat_count = properties.repeat_count or 20
    self.COMMIT_FOOTER_KEY = 'Validate-Test-Flakiness'
    self.build_count = properties.build_count or 100
    self.historical_query_count = properties.historical_query_count or 1000
    self.current_query_count = properties.current_query_count or 10000

  @property
  def test_suffix(self):
    return 'check flakiness'

  @property
  def check_for_flakiness(self):
    """Boolean to determine whether flakiness logic should be run for trybots.

    This needs to be enabled in order for the coordinating function of
    this module to execute.

    Returns:
        A boolean of whether the build is identifying new tests.
    """
    return self._check_for_flakiness

  def should_check_for_flakiness(self):
    """Returns whether the module should run checks for new test flakiness.

    At this time, it checks the list of affected file to see if any file is
    possible to add a new test.
    """
    affected_files = self.m.chromium_checkout.get_files_affected_by_patch()
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
        excluded_invs.update(
            self.get_invocations_from_change(
                change=current_change, step_name=step))

    # Find all task invocations of each build invocation and add these to
    # excluded.
    sub_invs = []
    for build_inv in excluded_invs:
      sub_invs.extend([
          str(inv)
          for inv in self.m.resultdb.get_included_invocations(build_inv)
      ])
    excluded_invs.update(sub_invs)

    self.m.step.active_result.presentation.logs[
        "excluded_invocation_list"] = sorted(excluded_invs)

    return excluded_invs

  def get_builder_invocation_history(self, builder_id, excluded_invs=None):
    """Gets a list of Invocation names for the most recent builds on a builder.

    Searches buildbucket for the ResultDB Invocation names of a specified number
    of most recent builds on a particular builder.

    Invocations represent containers of results and Invocation names can be used
    to map buildbucket builds to results in ResultDB.

    Args:
        builder_id (buildbucket.builder.proto.BuilderID message): The builder to
            search for build history from.
        excluded_invs (set of str): A set of ResultDB invocation name strings
            for invocations that we don't want to include in our invocation list
            returned. This is usually invocations associated with the current
            build that we don't want to consider historical invocations as they
            contain new tests from the current CL.

    Returns:
        A list of ResultDB Invocation names for the builds we want to
        query.
    """
    if excluded_invs is None:
      excluded_invs = set()
    step_name = 'fetch previously run invocations'
    predicate = builds_service_pb2.BuildPredicate(builder=builder_id)
    search_results = self.m.buildbucket.search(
        predicate=predicate,
        limit=self.build_count,
        report_build=False,
        fields=['infra.resultdb.invocation'],
        step_name=step_name)

    invs = [
        str(b.infra.resultdb.invocation)
        for b in search_results
        if str(b.infra.resultdb.invocation) and
        str(b.infra.resultdb.invocation) not in excluded_invs
    ]

    return invs

  def get_test_variants(self, inv_list, test_query_count=None, step_name=None):
    """Gets a set of (test_id, variant hash) tuples found in specific builds.

    This method searches ResultDB for the invocations specified, extracts the
    test_id and variant_hash fields, concatenates them into strings, and
    inserts them into a set for return.

    Args:
        inv_list (list of str): Invocation names for the invocations to query
            from ResultDB.
        test_query_count (int): The number of tests to query from ResultDB.
        step_name (str): The name of the step in which this call is made.

    Returns:
        A set of TestDefinition objects.
    """
    test_query_count = test_query_count or self.historical_query_count
    step_name = step_name or 'fetch test variants from ResultDB'
    inv_dict = self.m.resultdb.query(
        inv_ids=self.m.resultdb.invocation_ids(inv_list),
        limit=test_query_count,
        step_name=step_name)

    test_set = set()
    for inv in inv_dict.values():
      for test_result in inv.test_results:
        test_set.add(TestDefinition(test_result))

    return test_set

  def verify_new_tests(self,
                       prelim_tests,
                       excluded_invs,
                       builder,
                       page_size=10000):
    """Verify the newly identified tests are new by cross-checking ResultDB.

    Queries ResultDB for the instances of the given test_ids on the builder for
    the past day and iterates through response to eliminate any false positives
    from the preliminary new test list.
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
    results = self.m.resultdb.get_test_result_history(
        realm=self.m.buildbucket.builder_realm,
        test_id_regexp='|'.join(
            sorted(set(t.test_id for t in list(prelim_tests)))),
        variant_predicate=predicate_pb2.VariantPredicate(
            contains={'def': {
                'builder': builder
            }}),
        page_size=page_size,
        step_name='cross reference newly identified tests against ResultDB')

    for entry in results.entries:
      test = TestDefinition(entry.result)
      excluded = entry.result.name.split("/tests")[0] in excluded_invs
      if test in prelim_tests and not excluded:
        prelim_tests.remove(test)

    return prelim_tests

  def trim_new_tests(self, new_tests):
    if new_tests and len(new_tests) > self._max_test_targets:
      # There are more new tests detected than what we're permitting, so we're
      # taking a random subset to re-run
      res = random.sample(new_tests, self._max_test_targets)
      s = self.m.step('subset of new tests', cmd=None)
      s.presentation.step_text = (
          'the total number of new tests identified exceed what we permit {}, '
          'so a random subset of those tests have been selected.'.format(
              self._max_test_targets))
      s.presentation.logs['new_test_subset'] = '\n'.join([
          'test_id: {}, variant_hash: {}'.format(t.test_id, t.variant_hash)
          for t in res
      ])
      return res

    return new_tests

  def identify_new_tests(self, variant_step=None, history_step=None):
    """Coordinating method for identifying new tests on the current build.

    This method queries ResultDB for the historical tests run on the specified
    most recent builds on the current builder. This test list is compared with
    the tests running on the current build to identify and return new tests
    from the current CL.

    Args:
        variant_step (str): The name of the step where the test variants for the
          current build are found.
        history_step (str): The name of the step where the test variants for the
          historical builds are found.

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
      return set([])

    with self.m.step.nest('searching_for_new_tests') as p:
      current_builder = self.m.buildbucket.build.builder
      current_inv = str(self.m.buildbucket.build.infra.resultdb.invocation)
      excluded_invs = self.fetch_all_related_invocations()

      inv_list = self.get_builder_invocation_history(
          builder_id=current_builder, excluded_invs=excluded_invs)

      current_tests = self.get_test_variants(
          inv_list=[current_inv],
          test_query_count=self.current_query_count,
          step_name='fetch test variants for current patchset')
      p.logs['current_build_tests'] = join_tests(current_tests)

      historical_tests = self.get_test_variants(
          inv_list=inv_list,
          step_name='fetch test variants from previous invocations')
      p.logs['historical_tests'] = join_tests(historical_tests)

      # Comparing the current build test list to the ResultDB query test list to
      # get a preliminary set of potential new tests.
      preliminary_new_tests = current_tests.difference(historical_tests)
      p.logs['preliminary_tests'] = join_tests(preliminary_new_tests)

      # Cross-referencing the potential new tests with ResultDB to ensure they
      # are not present in existing builds.
      new_tests = self.verify_new_tests(
          prelim_tests=preliminary_new_tests,
          excluded_invs=excluded_invs,
          builder=current_builder.builder)
      p.logs['new_tests'] = ('new tests: \n\n{}'.format('\n'.join([
          'test_id: {}, variant_hash: {}, experimental: {}'.format(
              t.test_id, t.variant_hash, t.is_experimental)
          for t in self.m.py3_migration.consistent_ordering(
              new_tests, key=lambda t: (t.test_id, t.variant_hash))
      ])))

    return new_tests

  def find_tests_for_flakiness(self, test_objects):
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

    Returns:
      A list of step.Test objects
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

    if not self.should_check_for_flakiness():
      self.m.step('no test files were detected with this change.', cmd=None)
      return []

    new_tests = self.identify_new_tests()
    new_tests = self.trim_new_tests(new_tests)

    def _do_variants_match(test_object, new_test):
      # The 3 basic variants include builder, os, and test_suite. We compare
      # os through comparison of all dimensions.
      # * Builder we don't need to check, since we're comparing test results
      #   for the builder in question
      # see http://shortn/_Z3mUIaeQrB for variant_hash hashing alg.

      # Variants in testing/buildbot/ only update the naming. The device
      # information isn't uploaded to ResultDB, so we compare with test's
      # canonical name.
      variants = new_test.variants
      if ('test_suite' in variants and
          variants['test_suite'] != test_object.spec.canonical_name):
        return False

      if hasattr(test_object.spec, 'dimensions'):
        dimensions = test_object.spec.dimensions
        # Go through all variants, and if specified in 'dimensions', ensure that
        # the values are the same.
        for k, v in variants.items():
          if k in dimensions and dimensions[k] != v:
            return False

      # Non-swarming Test runs only record builder and test_suite, so we assume
      # that the other two basic variants match here.
      return True

    # This operation is O(len(test_obj) * len(new_tests)) because parsing
    # test_id is only intended for LUCI UI grouping, see
    # http://shortn/_StMScXolrz. max_test_targets will also bind the number of
    # iterations here. We loop the test objects and check all new tests to see
    # if the test_id start similarly.
    new_test_objects = []
    for test in test_objects:
      test_filter = []
      # find whether the Test object has a matching test_id.
      for new_test in new_tests:
        if (test.spec.test_id_prefix in new_test.test_id and
            _do_variants_match(test, new_test)):
          # test_id = test_id_prefix + {A full test_suite + test_name
          # representation}, so we use the test_id_prefix to split out
          # the test_suite and test_name
          test_filter.append(
              new_test.test_id.split(test.spec.test_id_prefix)[-1])
      if test_filter:
        test_copy = copy.copy(test)
        options = steps.TestOptions(
            test_filter=test_filter,
            repeat_count=self._repeat_count,
            retry_limit=0)
        test_copy._test_options = options

        # we only need one shard of the test spec to run a test instance
        # multiple times, we override whatever shard value was set prior to 1
        if isinstance(test.spec, steps.SwarmingTestSpec):
          test_copy.spec = test.spec.with_shards(1)
        new_test_objects.append(test_copy)

    return new_test_objects
