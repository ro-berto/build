# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from google.protobuf import json_format

from recipe_engine import recipe_test_api


class WeetbixTestApi(recipe_test_api.RecipeTestApi):

  def query_test_history(self, response, test_id, parent_step_name=None):
    """Emulates query_test_history() return value.
    Args:
      response: (luci.analysis.v1.test_history.QueryTestHistoryResponse) the
      response to simulate.
      test_id: (str) Test ID to query.
      parent_step_name: (str) The parent step name under which
        query_test_history is nested in, if any.
    """
    parent_step_prefix = ''
    if parent_step_name:
      parent_step_prefix = ('%s.' % parent_step_name)
    step_name = ('%sTest history query rpc call for %s' %
                 (parent_step_prefix, test_id))

    return self.step_data(
        step_name,
        self.m.json.output_stream(json_format.MessageToDict(response)))
