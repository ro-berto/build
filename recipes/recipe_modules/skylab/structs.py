# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Define the interface to call Skylab module."""

from RECIPE_MODULES.build.attr_utils import (attrs, attrib, enum_attrib,
                                             sequence_attrib, mapping_attrib)

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

# This file defines an interface for other recipes to interact with Skylab. As
# this module is designed for LaCrOS tests, the field exposed here are highly
# focusing on the LaCrOS use cases.
#
# Skylab tests are invoked via a luci rpc call to cros_test_platform builder,
# aka CTP. CTP supports multiple request in one build, where each request has
# an unique tag. A request executes an autotest suite test, which can wrapper
# one or more tast suites. Users must specify the autotest suite name in their
# request.
#
# As LaCrOS decided to use tast test framework, this module is designed to be
# more tast friendly by providing the tast suite result. See the CTP response
# below(go/ctp-resp):
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
# 1. instead of a raw CTP response, the module breaks it down and returns a list
#    of tast suite runs, contained in "attempts".
# 2. users can extract a specific result via the request tag and tast name.


@attrs()
class SkylabRequest(object):
  """Equivalent to a cros_test_platform request(go/ctp-req)

  SkylabRequest represents an autotest suite wrapping one or several tast
  suites.

  Attributes:
    * display_name: The step name to display in Milo frontend.
    * request_tag: The tag to identify a request in the CTP build.
    * suite: The autotest wrapper name, e.g. bvt-tast-chrome-pfq.
    * board: The CrOS build target name, e.g. eve, kevin.
    * cros_img: The GS path presenting CrOS image to provision the DUT,
                e.g. atlas-release/R88-13545.0.0
  """
  display_name = attrib(str)
  request_tag = attrib(str)
  suite = attrib(str)
  board = attrib(str)
  cros_img = attrib(str)

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)


@attrs()
class SkylabTestCase(object):
  """Describe a test case executed in a tast suite.

  Attributes:
    * name: test case name.
    * verdict: test case result.
  """
  name = attrib(str, default=None)
  verdict = enum_attrib(["PASSED", "FAILED", "UNSPECIFIED"],
                        default="UNSPECIFIED")

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
    * log_url: GS URI for the test logs.
    * test_cases: List of test cases contained in this suite.
  """
  url = attrib(str, default=None)
  status = enum_attrib([
      common_pb2.STATUS_UNSPECIFIED, common_pb2.INFRA_FAILURE,
      common_pb2.FAILURE, common_pb2.SUCCESS
  ],
                       default=common_pb2.STATUS_UNSPECIFIED)
  tast_suite = attrib(str, default=None)
  verdict = enum_attrib(["PASSED", "FAILED", "UNSPECIFIED"],
                        default="UNSPECIFIED")
  log_url = attrib(str, default=None)
  test_cases = sequence_attrib(SkylabTestCase, default=())

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)


@attrs()
class SkylabTaggedResponses(object):
  """A wrapper for all test results run in a CTP build.

  Attributes:
    * build_id: CTP's build ID.
    * responses: A mapping of request tag to the SkylabResponse.
    * status: Representation of the CTP build status.
  """
  build_id = attrib(int, default=0)
  responses = mapping_attrib(str)
  status = attrib(int, default=0)

  @classmethod
  def create(cls, **kwargs):
    return cls(**kwargs)