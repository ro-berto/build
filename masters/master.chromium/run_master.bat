@echo off
setlocal
title Chromium Master
set PYTHONPATH=..\..\third_party\buildbot_7_8;..\..\third_party\twisted_8_1;..\..\scripts;..\..\third_party;..\..\site_config;
set PATH=%~dp0..\depot_tools;%~dp0..\depot_tools\release\python_24;%~dp0..\depot_tools\python;%PATH%
python ..\..\scripts\common\twistd --no_save -y buildbot.tac
