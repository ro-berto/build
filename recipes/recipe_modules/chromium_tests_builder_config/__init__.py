# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'depot_tools/gsutil',
    'depot_tools/tryserver',
    'recipe_engine/platform',
    'recipe_engine/python',
]

# TODO(https://crbug.com/1128746) Until the test_specs field is removed from
# BuilderSpec, it needs to reference classes from the steps module, which would
# cause an import cycle, so they have been moved into
# chromium_tests_builder_config. To avoid having to duplicate chromium_tests
# tests to get full coverage, disable strict coverage so that the chromium_tests
# test will cover steps.py.
DISABLE_STRICT_COVERAGE = True

# Forward symbols for other modules to import
from .builder_config import BuilderConfig, delegate_to_builder_spec
from .builder_db import BuilderDatabase
from .builder_spec import BuilderSpec, COMPILE_AND_TEST, TEST, PROVIDE_TEST_SPEC
from .try_spec import TryDatabase, TryMirror, TrySpec, COMPILE_AND_TEST, COMPILE
