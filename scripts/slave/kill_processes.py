#!/usr/bin/python
# Copyright (c) 2006-2008 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to kill any leftover test processes, executed by buildbot.

Only works on Windows."""

import os
import subprocess
import sys


def KillAll(process_names):
  """Tries to kill all copies of each process in the processes list."""
  for process_name in process_names:
    Kill(process_name)

def Kill(process_name):
  command = ['taskkill.exe', '/f', '/t', '/im']
  subprocess.call(command + [process_name])


# rdpclip.exe is part of Remote Desktop.  It has a bug that sometimes causes
# it to keep the clipboard open forever, denying other processes access to it.
# Killing BuildConsole.exe usually stops an IB build within a few seconds.
# Unfortunately, killing devenv.com or devenv.exe doesn't stop a VS build, so
# we don't bother pretending.
processes=[
    # Utilities we don't build, but which we use or otherwise can't
    # have hanging around.
    'BuildConsole.exe',
    'httpd.exe',
    'outlook.exe',
    'perl.exe',
    'python_slave.exe',
    'rdpclip.exe',
    'svn.exe',

    # These processes are spawned by some tests and should be killed by same.
    # It may occur that they are left dangling if a test crashes, so we kill
    # them here too.
    'firefox.exe',
    #'iexplore.exe',
    #'ieuser.exe',
    'acrord32.exe',

    # When VC crashes during compilation, this process which manages the .pdb
    # file generation sometime hangs.
    'mspdbsrv.exe',
    # The JIT debugger may start when devenv.exe crashes.
    'vsjitdebugger.exe',
    # This process is also crashing once in a while during compile.
    'midlc.exe',

    # Things built by/for Chromium.
    'allocator_unittests.exe',
    'app_unittests.exe',
    'automated_ui_tests.exe',
    'base_unittests.exe',
    'browser_tests.exe',
    'bsdiff.exe',
    'chrome.exe',
    'chrome_frame_net_tests.exe',
    'chrome_frame_perftests.exe',
    'chrome_frame_reliability_tests.exe',
    'chrome_frame_tests.exe',
    'chrome_frame_unittests.exe',
    'chrome_launcher.exe',
    'chromedriver.exe',
    'codesighs.exe',
    'convert_dict.exe',
    'courgette.exe',
    'courgette_fuzz.exe',
    'courgette_minimal_tool.exe',
    'courgette_unittests.exe',
    'crash_cache.exe',
    'crash_service.exe',
    'debug_message.exe',
    'dump_cache.exe',
    'DumpRenderTree.exe',
    'fetch_client.exe',
    'fetch_server.exe',
    'ffmpeg_tests.exe',
    'ffmpeg_unittests.exe',
    'flush_cache.exe',
    'gcapi_test.exe',
    'generate_profile.exe',
    'gfx_unittests.exe',
    'googleurl_unittests.exe',
    'hresolv.exe',
    'image_diff.exe',
    'ImageDiff.exe',
    'installer_util_unittests.exe',
    'interactive_ui_tests.exe',
    'ipc_tests.exe',
    'layout_test_helper.exe',
    'LayoutTestHelper.exe',
    'maptsvdifftool.exe',
    'media_bench.exe',
    'media_unittests.exe',
    'memory_test.exe',
    'mfdecoder.exe',
    'mfplayer.exe',
    'mft_h264_decoder_example.exe',
    'mft_h264_decoder_unittests.exe',
    'mini_installer.exe',
    'mini_installer_test.exe',
    'minidump_test.exe',
    'mksnapshot.exe',
    'msdump2symdb.exe',
    'msmap2tsv.exe',
    'nacl_sandbox_tests.exe',
    'nacl_ui_tests.exe',
    'nacl64.exe',
    'ncdecode_table.exe',
    'ncdecode_tablegen.exe',
    'net_perftests.exe',
    'net_unittests.exe',
    'page_cycler_tests.exe',
    'perf_tests.exe',
    'player_wtl.exe',
    'plugin_tests.exe',
    'printing_unittests.exe',
    'protoc.exe',
    'qt_faststart.exe',
    'reliability_tests.exe',
    'rlz_unittests.exe',
    'sandbox_poc.exe',
    'sbox_integration_tests.exe',
    'sbox_unittests.exe',
    'sbox_validation_tests.exe',
    'scaler_bench.exe',
    'selenium_tests.exe',
    'setup.exe',
    'setup_unittests.exe',
    'startup_tests.exe',
    'stress_cache.exe',
    'sync_integration_tests.exe',
    'tab_switching_test.exe',
    'test_shell.exe',
    'test_shell_tests.exe',
    'tld_cleanup.exe',
    'ui_tests.exe',
    'unit_tests.exe',
    'url_fetch_test.exe',
    'v8_shell.exe',
    'v8_mksnapshot.exe',
    'v8_shell_sample.exe',
    'vectored_handler_tests.exe',
    'wav_ola_test.exe',
    'webkit_unit_tests.exe',
    'wow_helper.exe',
]

if '__main__' == __name__:
  sys.exit(KillAll(processes))
