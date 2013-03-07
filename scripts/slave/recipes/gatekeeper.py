#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Specifies how to launch the gatekeeper."""

import os

BASE_DIR = os.path.join(os.pardir, os.pardir, os.pardir)
SCRIPT_DIR = os.path.join(BASE_DIR, 'scripts')
script = os.path.join(SCRIPT_DIR, 'slave', 'gatekeeper_launch.py')
factory_properties = {'script': script}
