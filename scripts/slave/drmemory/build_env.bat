:: Sets up the environment for use with MSVS tools and CMake.
@echo off

setlocal
:: cmd for loops are really hard, so I hardcoded the list of MSVS paths.
set vcvars="%PROGRAMFILES%\Microsoft Visual Studio 11.0\VC\bin\vcvars32.bat"
if exist %vcvars% goto found_vcvars
set vcvars="%PROGRAMFILES%\Microsoft Visual Studio 10.0\VC\bin\vcvars32.bat"
if exist %vcvars% goto found_vcvars
:: VS 2008 vcvars isn't standalone, it needs this env var.
set VS90COMNTOOLS=%PROGRAMFILES%\Microsoft Visual Studio 9.0\Common7\Tools\
set vcvars="%PROGRAMFILES%\Microsoft Visual Studio 9.0\VC\bin\vcvars32.bat"
if exist %vcvars% goto found_vcvars

:found_vcvars
call %vcvars%

:: Add the normal CMake install path.
set PATH=%PROGRAMFILES%\CMake 2.8\bin;%PATH%

:: Add 7z.exe to PATH.
set PATH=%PROGRAMFILES%\7-Zip;%PATH%

echo Final PATH:
echo %PATH%
%*
