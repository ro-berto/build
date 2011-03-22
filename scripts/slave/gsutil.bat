set HOME=%USERPROFILE%
python %~dp0../command_wrapper/bin/command_wrapper.py -- python %~dp0../../third_party/gsutil/gsutil %*
