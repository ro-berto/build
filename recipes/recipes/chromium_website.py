# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.
"""Recipe for building and deploying the www.chromium.org static website."""

from recipe_engine.post_process import DropExpectation
from recipe_engine.recipe_api import Property

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
    'recipe_engine/runtime',
    'recipe_engine/step',
]

# pylint: disable=line-too-long
PROPERTIES = {
    'repository':
        Property(
            kind=str,
            default='https://chromium.googlesource.com/experimental/chromium_website'
        ),
}
# pylint: enable=line-too-long


def RunSteps(api, repository):
  # TODO(dpranke): Fill this in once the builders are alive.
  del api
  del repository


def GenTests(api):
  yield api.test(
      'ci',
      api.buildbucket.ci_build(),
      api.post_process(DropExpectation),
  )
