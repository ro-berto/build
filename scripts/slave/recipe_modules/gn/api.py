# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api

class GnApi(recipe_api.RecipeApi):

  _ARG_RE = re.compile('\s*(\w+)\s*=')
  _NON_LOCAL_ARGS = frozenset(['goma_dir', 'target_sysroot'])

  def default_args_presenter(self, result, args, location=None, text_limit=15):
    """Default presenter for GN args.

    The arguments will be presented one per line, with arguments that aren't
    useful for local repros moved to the end. The arguments will be presented
    either in the step_text or the logs, depending on the values of location and
    text_limit.

    Args:
      result: The step result to present the GN args on.
      args: The GN args to present.
      location: Controls where the GN args for the build should be presented. By
        default or if None, the args will be in step_text if the count of lines
        is less than text_limit or the logs otherwise. To force the presentation
        to the step_text or logs, use 'text' or 'logs', respectively.
     text_limit: The maximum number of lines of GN args to display in the
        step_text when using the default behavior for displaying GN args.
    """
    if location is not None:
      assert location in ('text', 'logs'), \
          "location must be None or one of 'text' or 'logs'"

    # Move arguments that aren't useful for local repros to the end for
    # presentation
    local_lines = []
    non_local_lines = []
    for l in args.splitlines():
      match = self._ARG_RE.match(l)
      if match is not None and match.group(1) in self._NON_LOCAL_ARGS:
        non_local_lines.append(l)
      else:
        local_lines.append(l)

    lines = local_lines + non_local_lines

    if location is None:
      if len(lines) > text_limit:
        result.presentation.step_text += (
            '<br/>Count of GN args (%d) exceeds limit (%d),'
            ' presented in logs instead') % (len(lines), text_limit)
        location = 'logs'

    if location == 'logs':
      result.presentation.logs['gn_args'] = lines
    else:
      result.presentation.step_text += '<br/>'.join([''] + lines)

  def get_args(self, build_dir, presenter=None, step_name='read GN args'):
    """Get the GN args for the build.

    A step will be executed that fetches the args.gn file and adds the contents
    to the presentation for the step.

    Args:
      build_dir: The Path to the build output directory. The args.gn file will
        be extracted from this location. The args.gn file must already exist (gn
        or mb should have already been run before calling this method).
      presenter: The callback used to present the GN args. It must be an object
        callable with two arguments:
          1. The step result.
          2. The GN args in the form of the content of the args.gn file.
        By default, gn.default_args_presenter will be used. To change the text
        limit or force it to present to the logs or text, use functools.partial.
        e.g.
          functools.partial(
             self.m.gn.default_args_presenter, location='logs')
      step_name: The name of the step for fetching the args.

    Returns:
      The content of the args.gn file.
    """
    args_file_path = build_dir.join('args.gn')
    fake_args = (
        'goma_dir = "/b/build/slave/cache/goma_client"\n'
        'target_cpu = "x86"\n'
        'use_goma = true\n')
    args = self.m.file.read_text(step_name, args_file_path, fake_args)

    (presenter or self.default_args_presenter)(self.m.step.active_result, args)

    return args
