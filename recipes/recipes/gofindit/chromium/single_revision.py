# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = ['recipe_engine/step']

def RunSteps(api):
  api.step('Print GoFindit', ['echo', 'hello', 'GoFindit'])

def GenTests(api):
  yield api.test('basic')