#!/bin/sh
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

while :
do
    cd /src/chromium/src
    # This somewhat quirky sequence of steps seems to clear up all the broken
    # git situations we've gotten ourself into in the past.
    # Remove any left-over layout test results, added files, etc.
    git clean -f -d > /dev/null 2>&1
    # If we got killed during a git rebase, we need to clean up.
    git rebase --abort > /dev/null 2>&1
    # Avoid updating the working copy to a stale revision.
    git fetch origin > /dev/null 2>&1
    git svn fetch
    # roll-blink-safely.py uses the blink_roll branch but does not know
    # how to clean up after itself.
    git branch -D master blink_roll > /dev/null 2>&1
    git checkout origin/master -f  > /dev/null 2>&1
    git checkout origin/master -b master > /dev/null 2>&1

    # Make sure auto-roll is up to date.
    cd /src/build/scripts/tools/blink_roller
    git pull --rebase

    # FIXME: We should probably remove any stale pyc files.
    ./auto_roll.py blink eseidel@chromium.org /src/chromium/src

    echo 'Waiting 5 minutes between checks...'
    sleep 300
done
