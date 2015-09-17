#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

import test_env  # pylint: disable=W0403,W0611

from recipe_engine import simulation_test
from slave import recipe_universe

if __name__ == '__main__':
  simulation_test.main(recipe_universe.get_universe())
