# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib

from slave import recipe_test_api


class BotUpdateTestApi(recipe_test_api.RecipeTestApi):
  def output_json(self, active, root, revision_mapping, git_mode):
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
              property_name: self.gen_revision(project_name, git_mode)
              for project_name, property_name in revision_mapping.iteritems()
          },
          'step_text': 'Some step text'
      })
    return self.m.json.output(output)


  @staticmethod
  def gen_revision(project, GIT_MODE):
    """Hash project to bogus deterministic revision values."""
    h = hashlib.sha1(project)
    if GIT_MODE:
      return h.hexdigest()
    else:
      import struct
      return struct.unpack('!I', h.digest()[:4])[0] % 300000
