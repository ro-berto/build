# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from PB.go.chromium.org.luci.buildbucket.proto \
    import builds_service as builds_service_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2


class FlakinessApi(recipe_api.RecipeApi):
  """A module for new test identification on try builds"""

  def __init__(self, properties, *args, **kwargs):
    super(FlakinessApi, self).__init__(*args, **kwargs)
    self._using_test_identifier = properties.identify_new_tests

  @property
  def using_test_identifier(self):
    """Whether the build is identifying and logging new tests introduced

    This needs to be enabled in order for the coordinating function of
    this module to execute.

    Return:
      (bool) whether the build is identifying new tests.
    """
    return self._using_test_identifier

  def get_associated_invocations(self):
    """Gets ResultDB Invocation IDs from the same CL as the current build

    An invocation represents a container of results, in this case from a
    buildbucket build. Invocation IDs map the buildbucket build to the ResultDB
    test results.

    Multiple builds can be triggered from the same CL and different patch sets.
    This method searches through all patch sets for the current build,
    gathers a list of the builds associated, and extracts the Invocation IDs
    from each build.

    Note: This does NOT get Invocation IDs associated with chained CLs.

    Returns:
      A set of ResultDB Invocation IDs as strings
    """
    step_name = 'fetching_builds_for_given_cl'
    change = self.m.buildbucket.build.input.gerrit_changes[0]

    # Creating BuildPredicate object for each patch set within a CL and
    # compiling them into a list. This is to search for builds from the
    # same CL but from different patch sets to exclude from our historical
    # data, ensuring all tests new to the CL are detected as new.
    predicates = []
    for i in range(1, change.patchset + 1):
      predicates.append(
          builds_service_pb2.BuildPredicate(gerrit_changes=[
              common_pb2.GerritChange(
                  host=change.host,
                  project=change.project,
                  change=change.change,
                  patchset=i)
          ]))

    search_results = self.m.buildbucket.search(
        predicate=predicates,
        step_name=step_name,
        fields=['builds.*.infra.resultdb.invocation'],
    )

    inv_set = set(
        # These invocation IDs will later be used to query ResultDB, which
        # explicitly requires strings
        str(build.infra.resultdb.invocation) for build in search_results)
    self.m.step.active_result.presentation.logs[
        "invocation_list_from_builds"] = sorted(inv_set)

    return inv_set
