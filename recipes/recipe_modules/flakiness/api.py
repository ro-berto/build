# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from PB.go.chromium.org.luci.buildbucket.proto \
    import builds_service as builds_service_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 import predicate as predicate_pb2


class FlakinessApi(recipe_api.RecipeApi):
  """A module for new test identification on try builds."""

  def __init__(self, properties, *args, **kwargs):
    super(FlakinessApi, self).__init__(*args, **kwargs)
    self._using_test_identifier = properties.identify_new_tests
    self.build_count = properties.build_count or 100
    self.historical_query_count = properties.historical_query_count or 1000
    self.current_query_count = properties.current_query_count or 10000

  @property
  def using_test_identifier(self):
    """Whether the build is identifying and logging new tests introduced.

    This needs to be enabled in order for the coordinating function of
    this module to execute.

    Returns:
        A boolean of whether the build is identifying new tests.
    """
    return self._using_test_identifier

  def get_associated_invocations(self):
    """Gets ResultDB Invocation names from the same CL as the current build.

    An invocation represents a container of results, in this case from a
    buildbucket build. Invocation names can be used to map the buildbucket build
    to the ResultDB test results.

    Multiple builds can be triggered from the same CL and different patch sets.
    This method searches through all patch sets for the current build,
    gathers a list of the builds associated, and extracts the Invocation names
    from each build.

    Note: This does NOT get Invocation names associated with chained CLs.

    Returns:
        A set of ResultDB Invocation names as strings.
    """
    change = self.m.buildbucket.build.input.gerrit_changes[0]

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
        step_name='fetching_builds_for_given_cl',
        fields=['infra.resultdb.invocation'],
    )

    inv_set = set(
        # These invocation names will later be used to query ResultDB, which
        # explicitly requires strings
        str(build.infra.resultdb.invocation) for build in search_results)
    self.m.step.active_result.presentation.logs[
        "excluded_invocation_list"] = sorted(inv_set)

    return inv_set

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
    step_name = 'get_historical_invocations'
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
        if str(b.infra.resultdb.invocation) not in excluded_invs
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
        A set of (test_id, test variant hash) tuples.
    """
    test_query_count = test_query_count or self.historical_query_count
    step_name = step_name or 'get_test_variants'
    inv_dict = self.m.resultdb.query(
        inv_ids=self.m.resultdb.invocation_ids(inv_list),
        limit=test_query_count,
        step_name=step_name)

    test_set = set()
    for inv in inv_dict.values():
      for test_result in inv.test_results:
        test_set.add((test_result.test_id, test_result.variant_hash))

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
      prelim_tests (set of tuples of str): the set of (test_id,test variant
        hash) tuples identified as potential new tests to be cross-referenced
        with ResultDB. This set will be modified by this method to contain only
        tests not found in ResultDB existing tests.
      excluded_invs (set of str): the invocation names belonging to builds
        associated with the current build to be excluded from existing tests.
      builder (str): The name of the builder to query test results for.
      page_size (int): The number of results to return from the ResultDB search.
        Defaults to 10,000, meaning the search will return a maximum of 10,000
        test results.

    Returns:
      A set of (test_id, test variant hash) tuples representing new tests.

    """
    results = self.m.resultdb.get_test_result_history(
        realm=self.m.buildbucket.builder_realm,
        test_id_regexp='|'.join(t[0] for t in list(prelim_tests)),
        variant_predicate=predicate_pb2.VariantPredicate(
            contains={'def': {
                'builder': builder
            }}),
        page_size=page_size,
        step_name='verify_new_tests')

    for entry in results.entries:
      test_tuple = (entry.result.test_id, entry.result.variant_hash)
      excluded = entry.result.name.split("/tests")[0] in excluded_invs
      if test_tuple in prelim_tests and not excluded:
        prelim_tests.remove(test_tuple)

    return prelim_tests

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
        A set of strings representing test_id + variant_hash concatenations
        for all tests present in the current build but absent in the historical
        build data.
    """

    def join_tests(test_set):
      """Joins set of test_id, variant hash tuples into strings.

      For step presentations, test tuple sets cannot be logged so it is
      necessary and preferred to convert to lists of sorted concatenated
      strings.
      """
      return sorted([
          '_'.join([test_id, variant_hash])
          for test_id, variant_hash in test_set
      ])

    if not self.using_test_identifier:
      return None

    variant_step = variant_step or 'get_current_cl_test_variants'
    history_step = history_step or 'get_historical_test_variants'

    with self.m.step.nest('searching_for_new_tests') as presentation:
      current_builder = self.m.buildbucket.build.builder
      current_inv = str(self.m.buildbucket.build.infra.resultdb.invocation)
      excluded_invs = self.get_associated_invocations()

      inv_list = self.get_builder_invocation_history(
          builder_id=current_builder, excluded_invs=excluded_invs)

      current_tests = self.get_test_variants(
          inv_list=[current_inv],
          test_query_count=self.current_query_count,
          step_name=variant_step)
      self.m.step.active_result.presentation.logs[
          'current_build_tests'] = join_tests(current_tests)
      historical_tests = self.get_test_variants(
          inv_list=inv_list, step_name=history_step)

      # Comparing the current build test list to the ResultDB query test list to
      # get a preliminary set of potential new tests.
      preliminary_new_tests = current_tests.difference(historical_tests)
      self.m.step.active_result.presentation.logs[
          'preliminary_tests'] = join_tests(preliminary_new_tests)

      # Cross-referencing the potential new tests with ResultDB to ensure they
      # are not present in existing builds.
      new_tests = self.verify_new_tests(
          prelim_tests=preliminary_new_tests,
          excluded_invs=excluded_invs,
          builder=current_builder.builder)
      presentation.logs['new_tests'] = join_tests(new_tests)
    return new_tests
