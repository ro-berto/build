# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class FinditApi(recipe_api.RecipeApi):

  def send_result_to_gofindit(self):
    # TODO (nqmtuan): Implement this step
    self.m.step('send_result_to_gofindit', ['echo', 'send_result_to_gofindit'])
