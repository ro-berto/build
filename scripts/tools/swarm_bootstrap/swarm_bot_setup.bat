:: Copyright (c) 2012 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: This script will setup the machine to be a swarm bot. It is assumed that
:: python is already installed on this system and the required swarm files have
:: been added.

:STARTUP_SCRIPT
echo Setup up swarm script to run on startup...
cd c:\Users\chrome-bot\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
echo @cd C:\swarm\ > run_swarm_bot.bat
echo @python xmlrpc_server.py >> run_swarm_bot.bat

:: We are done.
:END
shutdown -r -f -t 1