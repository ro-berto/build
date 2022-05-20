# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.chromium_tests_builder_config import properties

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'depot_tools/gsutil',
    'depot_tools/tryserver',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
]

PROPERTIES = properties.InputProperties

# Forward symbols for other modules to import
from .builder_config import (BuilderConfig, BuilderConfigException,
                             delegate_to_builder_spec)
from .builder_db import BuilderDatabase
from .builder_spec import BuilderSpec, COMPILE_AND_TEST, TEST
from .try_spec import (TryDatabase, TryMirror, TrySpec, COMPILE_AND_TEST,
                       COMPILE, ALWAYS, NEVER, QUICK_RUN_ONLY)
