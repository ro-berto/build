@echo off
setlocal
title Skia Master
set PYTHONPATH=..\..\third_party\buildbot_8_3p1;..\..\third_party\twisted_10_2;..\..\third_party\jinja2:..\..\scripts;..\..\third_party;..\..\site_config;..\..\..\build_internal\site_config;.
set PATH=%~dp0..\depot_tools;%~dp0..\depot_tools\python;%PATH%
python ..\..\scripts\common\twistd --no_save -y buildbot.tac
