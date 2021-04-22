# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(https://crbug.com/1128746) Until the test_specs field is removed from
# BuilderSpec, it needs to reference classes from the steps module, which would
# cause an import cycle, so they have been moved into
# chromium_tests_builder_config, bring all of the definitions from that module
# into this module so that code can continue to import from here
# pylint: disable=wildcard-import
from RECIPE_MODULES.build.chromium_tests_builder_config.steps import *
