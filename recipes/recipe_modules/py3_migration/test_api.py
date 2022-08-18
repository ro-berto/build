# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe module for managining incompatibilities between py2 and py3.

This provides a single point for dealing with differences between
python2 and python3 that manifest in recipe tests. This provides clear
indicators of extra code that is unnecessary once python2 support can be
removed.

The methods of this module cause minimal additional work to be performed
during actual recipe execution.
"""

from recipe_engine import recipe_test_api


class Py3MigrationTestApi(recipe_test_api.RecipeTestApi):

  def consistent_ordering(self, iterable, key=None):
    """Get an iterable with the same order between python versions.

    This allows for producing consistent expectation files where some
    aspect is determined by the iteration over a type that has different
    iteration order between python2 and python3 (e.g. dict or set).

    Args:
      iterable: The iterable to provide a consistent ordering for.
      key: A function taking an element of the iterable that provides
        the value to use for ordering the element.

    Returns:
      An iterable containing the same elements as the input iterable
      where the iteration order will be the same in python2 and python3
      but should otherwise be considered unspecified.
    """
    return sorted(iterable, key=key)
