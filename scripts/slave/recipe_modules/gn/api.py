# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api

from . import constants

class GnApi(recipe_api.RecipeApi):

  _DEFAULT_STEP_NAME = 'lookup GN args'
  _LOOKUP_ARGS_RE = re.compile(r'Writing """\\?\s*(.*)""" to _path_/args.gn',
                               re.DOTALL)
  _ARG_RE = re.compile('\s*(\w+)\s*=')
  _NON_LOCAL_ARGS = frozenset(['goma_dir', 'target_sysroot'])
  _DEFAULT_MAX_TEXT_LINES = 15

  DEFAULT = constants.DEFAULT
  TEXT = constants.TEXT
  LOGS = constants.LOGS

  def lookup_args(self, mb_path, mb_config_path, mastername, buildername,
                  step_name=None):
    """Run "mb lookup" to get the GN args for a builder.

    Args:
      mb_path - A Path object pointing at the directory that contains the mb tool.
      mb_config_path - A Path object pointing to the file containing the mb
        configurations.
      mastername - The name of the master the builder is a part of.
      buildername - The name of the builder to get the GN args for.

    Returns:
      A tuple containing the GN args as the first element and the step result
      from looking up the GN args as the second element. The GN args will be a
      single string in the same format as the content of the args.gn file.
    """
    args = [
        'lookup',
        '-m', mastername,
        '-b', buildername,
        '--config-file', mb_config_path,
    ]

    result = self.m.python(
        name=step_name or self._DEFAULT_STEP_NAME,
        script=mb_path.join('mb.py'),
        args=args,
        ok_ret='any',
        stdout=self.m.raw_io.output_text(),
        step_test_data=lambda: self.m.raw_io.test_api.stream_output(
            '\n'
            'Writing """\\\n'
            'goma_dir = "/b/build/slave/cache/goma_client"\n'
            'target_cpu = "x86"\n'
            'use_goma = true\n'
            '""" to _path_/args.gn.\n'
            '\n'
            '/fake-path/chromium/src/buildtools/linux64/gn gen _path_'
        ))

    match = self._LOOKUP_ARGS_RE.search(result.stdout)

    if not match:
      result.presentation.step_text = (
          'Failed to extract GN args from output of "mb lookup"')
      result.presentation.logs['mb lookup output'] = result.stdout.splitlines()
      result.presentation.status = self.m.step.EXCEPTION
      raise self.m.step.InfraFailure('Failed to extract GN args')

    return match.group(1), result

  def reformat_args(self, args):
    """Reformat the GN args to be more useful for local repros.

    Some of the arguments have values that are specific to individual runs and
    so a developer would likely not want to copy them to their own checkout when
    attempting to reproduce an issue locally. To enable ease of use, these
    arguments are moved to the end of the arguments so that a single contiguous
    region can be copied in order to create a build directory with the
    appropriate arguments.

    Args:
      args: A string containing the args.gn content to reformat.

    Returns:
      The reformatted args.gn content as a single string.
    """
    local_lines = []
    non_local_lines = []
    for l in args.splitlines():
      match = self._ARG_RE.match(l)
      if match is not None and match.group(1) in self._NON_LOCAL_ARGS:
        non_local_lines.append(l)
      else:
        local_lines.append(l)
    return '\n'.join(local_lines + non_local_lines)

  def present_args(self, result, args, location=None, max_text_lines=None):
    """Present the GN args.

    Args:
      result: The step result to present the GN args on.
      args: A string containing the args.gn content to present.
      location: Controls where the GN args for the build should be presented. By
        default or if gn.DEFAULT, the args will be in step_text if the count of
        lines is less than max_text_lines or the logs otherwise. To force the
        presentation to the step_text or logs, use gn.TEXT or gn.LOGS,
        respectively.
      max_text_lines: The maximum number of lines of GN args to display in the
        step_text when using the default behavior for displaying GN args.
    """
    location = location or self.DEFAULT
    assert location in (self.DEFAULT, self.TEXT, self.LOGS), \
        "location must be one of gn.DEFAULT, gn.TEXT or gn.LOGS"

    lines = args.splitlines()

    if location == self.DEFAULT:
      if max_text_lines is None:
        max_text_lines = self._DEFAULT_MAX_TEXT_LINES
      if len(lines) > max_text_lines:
        result.presentation.step_text += (
            '<br/>Count of GN args (%d) exceeds limit (%d),'
            ' presented in logs instead') % (len(lines), max_text_lines)
        location = self.LOGS

    if location == self.LOGS:
      result.presentation.logs['gn_args'] = lines
    else:
      result.presentation.step_text += '<br/>'.join([''] + lines)

  def get_args(self, mb_path, mb_config_path, mastername, buildername,
               location=None, max_text_lines=None, step_name=None):
    """Get the GN args for the build.

    A step will be executed that looks up the GN args and adds them to the
    presentation for the step.

    Args:
      build_dir: The Path to the build output directory. The args.gn file will
        be extracted from this location. The args.gn file must already exist (gn
        or mb should have already been run before calling this method).
      location: Controls where the GN args for the build should be presented. By
        default or if gn.DEFAULT, the args will be in step_text if the count of
        lines is less than max_text_lines or the logs otherwise. To force the
        presentation to the step_text or logs, use gn.TEXT or gn.LOGS,
        respectively.
      max_text_lines: The maximum number of lines of GN args to display in the
        step_text when using the default behavior for displaying GN args.
      step_name: The name of the step for reading the args.

    Returns:
      The GN args as a string in the same format as the content of the args.gn
      file.
    """
    args, result = self.lookup_args(
        mb_path, mb_config_path, mastername, buildername, step_name=step_name)
    if args is not None:
      reformatted_args = self.reformat_args(args)
      self.present_args(result, reformatted_args,
                        location=location, max_text_lines=max_text_lines)
    return args
