#!/bin/sh
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Sends a SIGTERM to a process whose PID is read from a pidfile.  Waits 10
# seconds for it to exit and then sends a SIGKILL.

set -e

pidfile="$1"

if [ -z "$pidfile" ]; then
  echo "Usage: $0 pidfile"
  exit 1
fi

if [ ! -e "$pidfile" ]; then
  echo "Pidfile $pidfile does not exist"
  exit 0
fi

pid=$(cat $pidfile)
pgid=$(ps h -o pgid= $pid | awk '{print $1}')

echo "Sending SIGTERM to PGID $pgid"
kill -TERM -$pgid

# Wait 10 seconds for it to exit.
for i in $(seq 100); do
  if ! ps -p $pid > /dev/null; then
    exit 0
  fi
  sleep 0.1
done

echo "Sending SIGKILL to PGID $pgid"
kill -KILL -$pgid
