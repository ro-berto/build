# Copyright (c) 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = 'PY3'

DEPS = [
    'recipe_engine/cas',
    'recipe_engine/cipd',
    'recipe_engine/file',
    'recipe_engine/futures',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'recipe_engine/swarming',
]
