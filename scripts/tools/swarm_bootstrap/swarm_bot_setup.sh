#!/bin/bash

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Setup the machine to run the required swarm commands on startup.
# It is assumed that python is already installed on this system and
# the required swarm files have been added.

echo Setup up swarm script to run on startup...
echo "@reboot cd $HOME/swarm && python xmlrpc_server.py" > mycron
crontab -r
crontab mycron
rm mycron
sudo shutdown -r now