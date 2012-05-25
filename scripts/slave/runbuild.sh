#!/bin/bash -e
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# runbuild.sh sets up PYTHONPATH to use runbuild.py straight from the CLI.
# this makes it easy to run and test buildsteps and builders.

BUILD=`cd ../../; pwd` # canonicalize path

PYTHONPATH="$BUILD/third_party/buildbot_8_4p1"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/buildbot_slave_8_4"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/twisted_10_2"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/jinja2"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/sqlalchemy_0_7_1"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/sqlalchemy_migrate_0_7_1"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/tempita_0_5"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/decorator_3_3_1"
PYTHONPATH="$PYTHONPATH:$BUILD/scripts"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party"
PYTHONPATH="$PYTHONPATH:$BUILD/site_config"
PYTHONPATH="$PYTHONPATH:$BUILD/../build_internal/site_config"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/setuptools-0.6c11"
PYTHONPATH="$PYTHONPATH:." python runbuild.py "$@"
