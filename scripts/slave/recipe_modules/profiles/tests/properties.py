# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium_checkout',
    'profiles',
    'recipe_engine/path',
]


def RunSteps(api):
  # fake path for start_dir
  api.chromium_checkout._working_dir = api.path['start_dir']

  # coverage only
  _ = api.profiles.merge_scripts_dir
  _ = api.profiles.merge_steps_script
  _ = api.profiles.merge_results_script
  _ = api.profiles.profile_subdirs
  _ = api.profiles.llvm_profdata_exec


def GenTests(api):

  yield api.test(
      'properties',
      api.post_process(post_process.DropExpectation),
  )
