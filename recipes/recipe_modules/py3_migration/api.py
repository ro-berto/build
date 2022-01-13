# Copyright (c) 2020 The Chromium Authors. All rights reserved.
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

import six

from recipe_engine import recipe_api


class Py3MigrationApi(recipe_api.RecipeApi):

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
      During recipe tests, an iterable containing the same elements as
      the input iterable where the iteration order will be the same in
      python2 and python3 but should otherwise be considered
      unspecified. During actual recipe execution, the input iterable
      will be returned.
    """
    if not self._test_data.enabled:
      return iterable  # pragma: no cover
    return self.test_api.consistent_ordering(iterable, key=key)

  def consistent_dict_str(self, d):
    """Get a dict string that is the same between python versions.

    This allows for producing consistent expectation files where some
    aspect is determined by the string representation of a dict, which
    will differ between python2 and python3 due to iteration order.

    Returns:
      During recipe tests, a string representation of the dict that will
      be the same in python2 and python3. During actual recipe
      execution, the default string representation of the dict will be
      returned.
    """
    if not self._test_data.enabled:
      return str(d)  # pragma: no cover
    key_value_str = ', '.join(
        '{!r}: {!r}'.format(k, v) for k, v in sorted(six.iteritems(d)))
    return '{{{}}}'.format(key_value_str)

  def consistent_exception_repr(self, e):
    """Get an exception repr that is the same between python versions.

    This allows for producing consistent expectation files where some
    aspect is determined by the repr of an exception, which will differ
    between python2 and python3 due to python2 including a trailing
    comma in the argument list when an exception is initialized with a
    single argument.

    Returns:
      During recipe tests, a repr of the exception that will be the same
      in python2 and python3. During actual recipe execution, the
      default repr will be used.
    """
    s = repr(e)
    if not self._test_data.enabled or six.PY3 or not s.endswith(',)'):
      return s
    return s[:-2] + ')'
