# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class FlakinessApi(recipe_api.RecipeApi):
  """A module for new test identification on try builds"""

  def __init__(self, properties, *args, **kwargs):
    super(FlakinessApi, self).__init__(*args, **kwargs)
    self._using_test_identifier = properties.identify_new_tests

  @property
  def using_test_identifier(self):
    """Whether the build is identifying and logging new tests introduced

    This needs to be enabled in order for the coordinating function of
    this module to execute.

    Return:
      (bool) whether the build is identifying new tests.
    """
    return self._using_test_identifier
