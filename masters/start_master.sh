#!/bin/sh
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Starts a master and waits for its pidfile to become live. This was split out
# of the Makefile in order to make a flock-able unit.

set -e

if [ -f twistd.pid ]; then
  PID=`cat twistd.pid`
  if [ -n "$(ps -p$PID -o pid=)" ]; then
    echo "twistd.pid has pid $PID which is still alive. aborting."
    exit 2
  fi
fi


echo 'Now running Buildbot master.'
python -S $SCRIPTS_DIR/common/twistd -y $TOPLEVEL_DIR/build/masters/buildbot.tac

echo 'Waiting for creation of twistd.pid...'
while `test ! -f twistd.pid`; do sleep 1; done;

PID=`cat twistd.pid`
echo "twistd.pid contains new buildbot pid $PID"
