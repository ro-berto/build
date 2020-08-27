# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from PB.recipe_modules.build.symupload import properties
from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import (steps, try_spec as
                                                 try_spec_module)

DEPS = ['recipe_engine/path', 'recipe_engine/properties', 'symupload']


def RunSteps(api):
  api.symupload(api.path['tmp_base'])


def GenTests(api):
  input_properties = properties.InputProperties()
  symupload_data = input_properties.symupload_datas.add()

  symupload_data.artifact = 'some_artifact.txt'
  symupload_data.url = 'https://some.url.com'

  yield api.test(
      'basic',
      api.path.exists(api.path['tmp_base'].join('symupload')),
      api.symupload(input_properties),
      api.post_process(post_process.StatusSuccess),
  )

  yield api.test(
      'no symupload binary',
      api.symupload(input_properties),
      api.post_process(post_process.StepFailure, 'Symupload'),
      api.post_process(post_process.StatusFailure),
  )

  yield api.test(
      'no action',
      api.symupload(properties.InputProperties()),
      api.post_process(post_process.DoesNotRun, 'Symupload'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
