# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import (steps, try_spec as
                                                 try_spec_module)

DEPS = [
    'chromium_checkout',
    'profiles',
    'recipe_engine/assertions',
    'recipe_engine/path',
]


def RunSteps(api):
  # fake path for start_dir
  api.chromium_checkout._working_dir = api.path['start_dir']

  api.profiles.merge_profdata('some_artifact', '.*', sparse=True)


def GenTests(api):

  yield api.test(
      'basic',
      api.post_process(post_process.MustRun,
                       'merge all profile files into a single .profdata'),
      api.post_process(post_process.DropExpectation),
  )
