@echo off
setlocal
title Dart Master
set PYTHONPATH=..\..\..\build\third_party\buildbot_7_12;..\..\..\build\third_party\twisted_8_1;..\..\..\build\scripts;..\..\..\build\third_party;..\..\..\build\site_config;..\..\site_config;..\..\scripts\master.
set PATH=%~dp0..\..\build\depot_tools;%~dp0..\..\build\depot_tools\release\python_24;%~dp0..\..\build\depot_tools\python;%PATH%
python ..\..\..\build\scripts\common\twistd --no_save -y buildbot.tac
