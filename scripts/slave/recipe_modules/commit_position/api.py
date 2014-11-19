# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from slave import recipe_api


class CommitPositionApi(recipe_api.RecipeApi):
  """Recipe module providing commit position parsing and manipulation."""
  RE_COMMIT_POSITION = re.compile('(?P<branch>.+)@{#(?P<revision>\d+)}')

  @classmethod
  def parse(cls, value):
    match = cls.RE_COMMIT_POSITION.match(value)
    if not match:
      raise ValueError("Invalid commit position (%s)" % (value,))
    return match.group('branch'), int(match.group('revision'))

  @classmethod
  def parse_branch(cls, value):
    branch, _ = cls.parse(value)
    return branch

  @classmethod
  def parse_revision(cls, value):
    _, revision = cls.parse(value)
    return revision

  @classmethod
  def construct(cls, branch, value):
    value = int(value)
    return '%(branch)s@{#%(value)d}' % {
        'branch': branch,
        'value': value,
    }
