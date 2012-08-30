#!/bin/bash
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Setup this mac machine to access the swarm network storage. This script must
# be run as root.
MAILTO=csharp@google.com
MOUNT_COMMAND="mount "$1":/vol/swarm_data /mnt/swarm_data"

echo Adding Root Crontab to Mount Network Drive...
mkdir -p /mnt/swarm_data
echo "@reboot /bin/sleep 60 && "$MOUNT_COMMAND > mycron
crontab -r
crontab mycron
rm mycron
