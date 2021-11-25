# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api
from recipe_engine.post_process import (
    Filter, DoesNotRun, DoesNotRunRE, DropExpectation, MustRun,
    ResultReasonRE, StatusException, StatusFailure, StepException)
from recipe_engine.recipe_api import Property

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
]

def RunSteps(api):
  pass



def GenTests(api):
  yield api.test("empty")