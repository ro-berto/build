@echo off
setlocal
title Chromium Clobber LKGR Poller
set PYTHONPATH=..\..\third_party\buildbot_7_12;..\..\third_party\twisted_8_1;..\..\scripts;..\..\third_party;
set PATH=%~dp0..\depot_tools;%~dp0..\depot_tools\release\python_24;%~dp0..\depot_tools\python;%PATH%
cd %~dp0
python lkgr_poller.py
