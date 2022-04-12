# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Define the interface to call Skylab module."""

from RECIPE_MODULES.build.attr_utils import attrs, attrib, enum
from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB

SKYLAB_TAST_TEST = 'tast_test'
SKYLAB_GTEST = 'gtest'

# This file defines an interface for browser recipes to call Skylab.
# As of 2021Q3, Skylab tests are invoked via a prpc call to cros_test_platform
# builder, aka CTP. Each CTP build represents a test suite, either tast or
# gtest. Chromium tests depend on ResultDB to get the result, so this interface
# does not parse the CTP's response.


@attrs()
class SkylabRequest(object):
  """Equivalent to a cros_test_platform request(go/ctp-req)

  SkylabRequest represents a Chromium tast or gtest suite.

  Attributes:
    * request_tag: The tag to identify a request from CTP build(s). Within a
          Chromium/Chrome build, each skylab test has its unique request_tag.
    * board: The CrOS build target name, e.g. eve, kevin.
    * cros_img: The GS path presenting CrOS image to provision the DUT,
          e.g. atlas-release/R88-13545.0.0
    * secondary_board: The CrOS build target name for secondary DUT.
    * secondary_cros_img: The GS path presenting CrOS image to provision the
          secondary DUT, e.g. atlas-release/R88-13545.0.0
    * dut_pool: The skylab device pool to run the test. By default the
          quota pool, shared by all CrOS tests.
    * lacros_gcs_path: The GCS full path pointing to a Lacros artifact.
          e.g. gs://lacros-poc/lacros-builder/101/lacros.
          If empty, DUT runs tests on the chrome bundled with the OS image.
    * exe_rel_path: The relative path of the test executable to src dir. For
          tast test, it is the chrome binary, e.g. out/Release/chrome. For
          gtest, it should be the executable test runner, e.g.
          out/Release/bin/run_ozone_unittests.
    * timeout_sec: The timeout for the test in second. Default is one hour.]
    * test_type: The type of the test, by default gtest. If the request has
          non-empty tast_expr, then tast_test.
    * tast_expr: The tast expression defines what tast test we run on the
          Skylab DUT, e.g. lacros.Basic.
    * tast_expr_file: The relative path of the filter file for tast tests. The
          filter stores tast expression in a dict. Users need to provide the
          tast_expr_key to extract them.
    * tast_expr_key: The key to extract the tast expression from the
          tast_expr_file.
    * test_args: The runtime argument for test,
          e.g. '--gtest_filter="VaapiTest.*'.
    * autotest_name: The name of the autotest to be executed in Skylab.
          This is tied to an autotest control file that contains setup
          informations and runs the actual test. For tast test, an
          autotest wrapper is required. e.g. tast.lacros
    * retries: The max that CTP will retry a request. Default is 0, no retry and
          max is 5.
    * resultdb: The ResultDB integration configuration, defined in
          chromium_tests/resultdb.py.
  """
  request_tag = attrib(str)
  board = attrib(str)
  cros_img = attrib(str)
  secondary_board = attrib(str, default='')
  secondary_cros_img = attrib(str, default='')
  dut_pool = attrib(str, default='')
  lacros_gcs_path = attrib(str, default='')
  exe_rel_path = attrib(str, default='')
  timeout_sec = attrib(int, default=3600)
  test_type = attrib(
      enum([SKYLAB_TAST_TEST, SKYLAB_GTEST]), default=SKYLAB_GTEST)
  tast_expr = attrib(str, default='')
  tast_expr_file = attrib(str, default='')
  tast_expr_key = attrib(str, default='')
  test_args = attrib(str, default='')
  autotest_name = attrib(str, default='')
  retries = attrib(enum([0, 1, 2, 3, 4, 5]), default=0)
  resultdb = attrib(ResultDB, default=None)

  @classmethod
  def create(cls, **kwargs):
    test_type = SKYLAB_TAST_TEST if kwargs.get('tast_expr') or kwargs.get(
        'tast_expr_file') else SKYLAB_GTEST
    return cls(test_type=test_type, **kwargs)
