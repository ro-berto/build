# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'goma',
    'depot_tools/depot_tools',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/python',
    'recipe_engine/file',
    'recipe_engine/step',
    'recipe_engine/tricium',
]

_clang_tidy_path = ('third_party', 'llvm-build', 'Release+Asserts', 'bin',
                    'clang-tidy')
