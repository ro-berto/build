# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib

from slave import recipe_test_api


class BotUpdateTestApi(recipe_test_api.RecipeTestApi):
  def output_json(self, active, root):
    """Deterministically synthesize json.output test data for gclient's
    --output-json option.
    """
    output = {
        'did_run': active
    }

    # Add in extra json output if active.
    if active:
      output.update({
          'root': root or 'src',
          'properties': {
              'foo': 'bar'
          },
          'step_text': 'Some step text'
      })
    return self.m.json.output(output)
