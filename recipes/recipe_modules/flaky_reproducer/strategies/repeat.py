# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .base import BaseStrategy


class RepeatStrategy(BaseStrategy):
  name = 'repeat'

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
