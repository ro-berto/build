#!/bin/sh
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Triggers a recipe on Swarming.
#
# Run this script with --build-properties from an actual build. Find a green
# build on:
# http://build.chromium.org/p/tryserver.chromium.linux/builders/linux_chromium_rel_ng
# Open first step stdio and set "try_job_key" value to "".
#

# The blacklist skips all the recipes expectations, which is the largest chunk
# of files being archived.
~/src/swarming/client/isolate.py archive -I https://isolateserver.appspot.com \
  -i recipes.isolate -s recipes.isolated --blacklist '.*\.expected'

# - PYTHONPATH=../..:../../../site_config is because build/scripts/ and
#   build/site_config are implicitly assumed to be in PYTHONPATH.
# - RUN_SLAVE_UPDATED_SCRIPTS=1 disables the gclient sync that would fail.
~/src/swarming/client/swarming.py trigger -I https://isolateserver.appspot.com \
  -S https://chromium-swarm.appspot.com recipes.isolated \
  --env PYTHONPATH ../..:../../../site_config \
  --env RUN_SLAVE_UPDATED_SCRIPTS 1 \
  -d os Linux \
  -d machine_type n1-standard-16 \
  -- '--factory-properties={"recipe":"chromium_trybot"}' \
  "$@"
