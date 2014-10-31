# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_test_api

class GitilesTestApi(recipe_test_api.RecipeTestApi):
  def _make_gitiles_response_json(self, data):
    return self.m.json.output(data)

  def make_refs_test_data(self, *refs):
    return self._make_gitiles_response_json({ref: None for ref in refs})

  def make_log_test_data(self, s, n=3):
    return self._make_gitiles_response_json({
      'log': [
        {
          'commit': 'fake %s hash %d' % (s, i),
          'author': {
            'email': 'fake %s email %d' % (s, i),
          },
        } for i in xrange(n)
      ],
    })
