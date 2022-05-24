# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium_checkout',
    'profiles',
    'recipe_engine/assertions',
    'recipe_engine/path',
]


def RunSteps(api):
  api.profiles.src_dir = api.chromium_checkout.src_dir
  api.profiles.merge_profdata('some_artifact', '.*', sparse=True)


def GenTests(api):

  yield api.test(
      'basic',
      api.post_process(post_process.MustRun,
                       'merge all profile files into a single .profdata'),
      api.post_process(post_process.DropExpectation),
  )
