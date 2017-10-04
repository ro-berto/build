# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

import os
import re
import sys
import traceback


_STDLIB_PATH = os.path.dirname(traceback.__file__)

_SKIPPING_MSG = '  <skipping stdlib frames that depend on python version>\n'

_SANITIZED_DIRS = '|'.join(re.escape(d) for d in [
  '.recipe_deps',
  'infra',
  'recipe_engine',
  'recipe_modules',
  'recipes',
])


class TracebackApi(recipe_api.RecipeApi):
  def _format_exc_filtered(self):
    """Formats the exception, preprocessing and filtering stack frames.

    The implementation follows traceback.format_exc() with processing injected
    in the middle.
    """
    etype, value, tb = sys.exc_info()
    if not tb:  # pragma: no cover
      return ''.join(traceback.format_exception_only(etype, value))

    out = ['Traceback (most recent call last):\n']

    pending = []
    for entry in traceback.extract_tb(tb):
      entry = self._filter_frame(entry)
      if entry:
        pending.append(entry)
      else:
        # Stumbled upon a skipped frame. Flush all we have now and add a cut
        # marker, if not already there.
        out += traceback.format_list(pending) if pending else []
        pending = []
        if not out or out[-1] != _SKIPPING_MSG:
          out.append(_SKIPPING_MSG)
    out += traceback.format_list(pending) if pending else []
    out += traceback.format_exception_only(etype, value)

    return ''.join(out)

  def _filter_frame(self, frame):
    filename, lineno, func, text = frame

    # Skip stdlib frames completely. They depend on version of Python.
    if filename.startswith(_STDLIB_PATH):
      return None

    # Make the traceback appear in "native" format by replacing the path
    # separators.
    filename = filename.replace(os.path.sep, self.m.path.sep)

    # Replace absolute paths to files with something that doesn't depend on the
    # source checkout location.
    filename = re.sub(
        re.escape(self.m.path.sep).join(['.*', '('+ _SANITIZED_DIRS + ')', '']),
        lambda m: self.m.path.sep.join(['<...>', m.group(1), '']),
        filename)

    return filename, lineno, func, text

  def format_exc(self):
    """Returns a string containing an exception traceback.

    Calls traceback.format_exc but during testing removes absolute paths.
    """
    if self._test_data.enabled:
      return self._format_exc_filtered()
    return traceback.format_exc()  # pragma: no cover
