# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Define the interface to call Skylab module."""

from RECIPE_MODULES.build.attr_utils import (attrs, attrib, enum, sequence,
                                             mapping)
from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

SKYLAB_TAST_TEST = 'tast_test'
SKYLAB_GTEST = 'gtest'

# This file defines an interface for other recipes to interact with Skylab. As
# this module is designed for Lacros tests, the field exposed here are highly
# focusing on the Lacros use cases.
#
# Skylab tests are invoked via a luci rpc call to cros_test_platform builder,
# aka CTP. CTP supports multiple request in one build, where each request has
# an unique tag. A request executes an autotest test, which wraps one tast or
# gtest suite. All skylab tests from Chromium/Chrome recipe land to our
# pre-defined autotest wrapper, tast.lacros for tast tests and lacros_gtest
# for gtest tests.
#
# See the CTP response below(go/ctp-resp):
# ````
# responses(autotest suite response)
#  +
#  |
#  +-> consolidated_results
#       |
#       +-> attempts(skylab test runner response, representing a tast suite run)
#              |
#              +-> test_cases
# ```
# 1. instead of a raw CTP response, this module breaks it down and returns a
#    list of tast/gtest suite runs, contained in "attempts".
# 2. users can extract a specific result via the request tag, aka test name.


@attrs()
class SkylabRequest(object):
  """Equivalent to a cros_test_platform request(go/ctp-req)

  SkylabRequest represents an autotest suite wrapping one or several tast
  suites.

  Attributes:
    * request_tag: The tag to identify a request from CTP build(s). Within a
          Chromium/Chrome build, each skylab test has its unique request_tag.
    * board: The CrOS build target name, e.g. eve, kevin.
    * cros_img: The GS path presenting CrOS image to provision the DUT,
          e.g. atlas-release/R88-13545.0.0
    * dut_pool: The skylab device pool to run the test. By default the
          quota pool, shared by all CrOS tests.
    * lacros_gcs_path: The GCS full path pointing to a Lacros artifact.
          e.g. gs://lacros-poc/lacros-builder/101/lacros.zip.
          TODO(crbug/1187717): Update this part once we support gtest.
          For lacros tast test, the GCS object equals to build dir, e.g.
          out/Release, with selected files.
          If empty, DUT runs tests on the chrome bundled with the OS image.
    * exe_rel_path: The relative path of the test executable to src dir. For
          tast test, it is the chrome binary, e.g. out/Release/chrome.
    * timeout_sec: The timeout for the test in second. Default is one hour.]
    * test_type: The type of the test, by default gtest. If the request has
          non-empty tast_expr, then tast_test.
    * tast_expr: The tast expression defines what tast test we run on the
          Skylab DUT, e.g. lacros.Basic.
    * test_args: The runtime argument for test,
          e.g. '--gtest_filter="VaapiTest.*'.
    * retries: The max that CTP will retry a request. Default is 0, no retry and
          max is 5.
    * resultdb: The ResultDB integration configuration, defined in
          chromium_tests/resultdb.py.
  """
  request_tag = attrib(str)
  board = attrib(str)
  cros_img = attrib(str)
  dut_pool = attrib(str, default='')
  lacros_gcs_path = attrib(str, default='')
  exe_rel_path = attrib(str, default='')
  timeout_sec = attrib(int, default=3600)
  test_type = attrib(
      enum([SKYLAB_TAST_TEST, SKYLAB_GTEST]), default=SKYLAB_GTEST)
  tast_expr = attrib(str, default='')
  test_args = attrib(str, default='')
  retries = attrib(enum([0, 1, 2, 3, 4, 5]), default=0)
  resultdb = attrib(ResultDB, default=None)

  @classmethod
  def create(cls, **kwargs):
    test_type = SKYLAB_TAST_TEST if kwargs.get('tast_expr') else SKYLAB_GTEST
    return cls(test_type=test_type, **kwargs)


@attrs()
class SkylabTestCase(object):
  """Describe a test case executed in a tast suite.

  Attributes:
    * name: test case name.
    * verdict: test case result.
  """
  name = attrib(str, default=None)
  verdict = attrib(
      enum(["PASSED", "FAILED", "UNSPECIFIED"]), default="UNSPECIFIED")

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)


@attrs()
class SkylabResponse(object):
  """Equivalent to a skylab test runner response.

  SkylabResponse represents the result of a tast suite

  Attributes:
    * url: The URL to view the Skylab test runner's execution details.
    * status: Representation of a Skylab test run's status, translated from
          skylab test runner's lifecycle and verdict.
    * tast_suite: tast suite name.
    * verdict: test result.
    * log_url: Stainless log URL for humans to view.
    * log_gs_uri: GCS URI for the log at which skylab logs are stored
    * test_cases: List of test cases contained in this suite.
  """
  url = attrib(str, default=None)
  status = attrib(
      enum([
          common_pb2.STATUS_UNSPECIFIED, common_pb2.INFRA_FAILURE,
          common_pb2.FAILURE, common_pb2.SUCCESS
      ]),
      default=common_pb2.STATUS_UNSPECIFIED)
  tast_suite = attrib(str, default=None)
  verdict = attrib(
      enum(["PASSED", "FAILED", "UNSPECIFIED"]), default="UNSPECIFIED")
  log_url = attrib(str, default=None)
  log_gs_uri = attrib(str, default=None)
  test_cases = attrib(sequence[SkylabTestCase], default=())

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)


@attrs()
class SkylabTaggedResponses(object):
  """A wrapper for all test results run in a CTP build.

  Attributes:
    * build_id: CTP's build ID.
    * responses: A mapping of request tag to the list of SkylabResponses.
    * status: Representation of the CTP build status.
  """
  build_id = attrib(int, default=0)
  responses = attrib(mapping[str, sequence[SkylabResponse]])
  status = attrib(int, default=0)

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)
