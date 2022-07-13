# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from ..test_binary import create_test_binary_from_jsonish


class ReproducingStep:
  """Containing the information needed to reproduce a flaky test failure.

  Attributes:
    test_binary (TestBinary): The test binary with preset settings using with_*
      methods.
    reproducing_rate (float): Reproducing rate by running the given test binary.
      This is different from failure rate, as failed runs / total runs. A test
      binary could rerun the test multiple times and only need to fail once to
      be counted as reproduced.
    duration (int): Duration in milliseconds of the total running time of the
      given test binary. It should contains all the retries if applied.
  """

  def __init__(self, test_binary, reproducing_rate=0, duration=0, **other):
    self.test_binary = test_binary
    self.reproducing_rate = reproducing_rate
    self.duration = duration
    self.debug_info = other

  def to_jsonish(self):
    ret = dict(
        test_binary=self.test_binary.to_jsonish(),
        reproducing_rate=self.reproducing_rate,
        duration=self.duration)
    ret.update(self.debug_info)
    return ret

  @classmethod
  def from_jsonish(cls, json_data):
    test_binary = create_test_binary_from_jsonish(json_data.pop('test_binary'))
    return cls(test_binary, **json_data)

  def readable_info(self):
    """Returns Human readable instruction of the reproducing steps."""
    if not self.reproducing_rate:
      return 'This failure was NOT reproduced on {0}.'.format(
          self.test_binary.dimensions.get('os', 'unknown-os'))
    message = []
    message.append(
        'This failure could be reproduced ({0:.1f}%) with command'.format(
            self.reproducing_rate * 100))
    if self.test_binary.dimensions.get('os', None):
      message.append(' on {0}'.format(self.test_binary.dimensions['os']))
    if self.debug_info.get('strategy_name', None):
      message.append(' with {0}'.format(self.debug_info['strategy_name']))
    message.append(':')
    message.append('\n\n')
    message.append(self.test_binary.readable_command())
    return ''.join(message)

  def better_than(self, other):
    """Returns if this reproducing step works better than the other.

    It's mainly measured by reproducing_rate. If the two reproducing step have
    similar reproducing_rate >= 0.9, the shorter running duration is better.
    """
    if self.reproducing_rate >= 0.9 and other.reproducing_rate >= 0.9 and abs(
        self.reproducing_rate - other.reproducing_rate) < 0.03:
      return self.duration < other.duration
    return self.reproducing_rate > other.reproducing_rate
