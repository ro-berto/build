# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .base import BaseStrategy


class RepeatStrategy(BaseStrategy):
  name = 'repeat'

  def run(self, timeout=45 * 60):
    pass
