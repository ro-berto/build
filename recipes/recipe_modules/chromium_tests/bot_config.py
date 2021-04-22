# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(https://crbug.com/1193832) Remove this file once all uses have
# been switched to chromium_tests_builder_config
from RECIPE_MODULES.build.chromium_tests_builder_config import (BuilderConfig as
                                                                BotConfig)

from .target_config import TargetConfig as BuildConfig