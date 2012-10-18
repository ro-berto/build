#!/bin/bash

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Setup the machine to run the required swarm commands on startup.
# It is assumed that python is already installed on this system and
# the required swarm files have been added.

DIMENSIONS_FILE="dimension.in"
SLAVE_ARGUMENTS="-a https://chromium-swarm.appspot.com -p 443 -r 400 -v "$DIMENSIONS_FILE
SLAVE_COMMAND="python slave_machine.py "$SLAVE_ARGUMENTS

echo Generate the machine dimensions...
cd $HOME/swarm
python dimensions_generator.py $DIMENSIONS_FILE

echo Setup up swarm script to run on startup...
echo "@reboot cd $HOME/swarm && "$SLAVE_COMMAND > mycron
crontab -r
crontab mycron
rm mycron
sudo shutdown -r now