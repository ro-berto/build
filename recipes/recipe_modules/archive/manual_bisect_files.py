# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Defines variables necessary to make lightweight linux perf builds.

Declares required files and whitelisted files to run manual bisect
script on perf builds. Binary files that should be
stripped to reduce zip file size are declared. The file list was
gotten from the local chrome executable path. (This can be retrieved by
typing 'chrome://version' in chrome and following the executable path.
The list needs to be updated if future chrome versions require additional files.
"""
CHROME_REQUIRED_FILES = {
    'android': [
        'apks',
        'apks/*',
    ],
    'linux': [
        'chrome',
        'chrome_100_percent.pak',
        'chrome_200_percent.pak',
        'chromedriver',
        'default_apps',
        'default_apps/*',
        'icudtl.dat',
        'libclearkeycdm.so',
        'libclearkeycdmadapter.so',
        'libwidevinecdm.so',
        'libwidevinecdmadapter.so',
        'locales',
        'locales/*',
        'nacl_helper',
        'nacl_helper_bootstrap',
        'nacl_helper_nonsfi',
        'nacl_irt_x86_64.nexe',
        'PepperFlash',
        'PepperFlash/*',
        'pnacl',
        'pnacl/*',
        'product_logo_48.png',
        'resources',
        'resources/*',
        'resources.pak',
        'v8_context_snapshot.bin',
        'xdg-mime',
        'xdg-settings',
    ],
    'win': [
        'chrome.dll',
        'chrome.exe',
        'chrome_100_percent.pak',
        'chrome_200_percent.pak',
        'chrome_child.dll',
        'chrome_elf.dll',
        'chrome_watcher.dll',
        'chromedriver.exe',
        'default_apps',
        'default_apps/*',
        'd3dcompiler_47.dll',
        'icudtl.dat',
        'libEGL.dll',
        'libGLESv2.dll',
        'locales',
        'locales/*',
        'nacl_irt_x86_64.nexe',
        'PepperFlash',
        'PepperFlash/*',
        'resources.pak',
        'SecondaryTile.png',
        'v8_context_snapshot.bin',
        'WidevineCdm',
        'WidevineCdm/*',
    ],
    'mac': [
        'chromedriver',
        'Google Chrome.app',
        'Google Chrome.app/*',
    ],
    'fuchsia': [
        'chromedriver',
        'gen',
        'gen/chrome',
        'gen/chrome/app',
        'gen/chrome/app/chrome',
        'gen/chrome/app/chrome/chrome.far',
        'gen/fuchsia_web',
        'gen/fuchsia_web/runners',
        'gen/fuchsia_web/runners/cast_runner',
        'gen/fuchsia_web/runners/cast_runner/cast_runner.far',
        'gen/fuchsia_web/webengine',
        'gen/fuchsia_web/webengine/web_engine',
        'gen/fuchsia_web/webengine/web_engine/web_engine.far',
        'gen/fuchsia_web/shell',
        'gen/fuchsia_web/shell/web_engine_shell',
        'gen/fuchsia_web/shell/web_engine_shell/web_engine_shell.far',
    ],
    # As of 2022/2, this only represents Lacros.
    'chromeos': [
        'chrome',
        'chrome_100_percent.pak',
        'chrome_200_percent.pak',
        'chrome_crashpad_handler',
        'headless_lib_data.pak',
        'headless_lib_strings.pak',
        'icudtl.dat',
        'metadata.json',
        'nacl_helper',
        # nacl_irt*.nexe file is in the whitelist section below.
        'resources.pak',
        'snapshot_blob.bin',
        'locales',
        'locales/*',
        'swiftshader',
        'swiftshader/*',
        'WidevineCdm',
        'WidevineCdm/*',
    ],
}

CHROME_WHITELIST_FILES = {
    'linux': '',
    'win': '^\d+\.\d+\.\d+\.\d+\.manifest$',
    'mac': '',
    # For amd64, we need "nacl_irt_x86_64.nexe" and
    # for arm, we need "nacl_irt_arm.nexe". Since there is no way
    # to specify files per architecture, we use regex to include it.
    'chromeos': 'nacl_irt_.*',
}

CHROME_STRIP_LIST = {
  'linux': [
    'chrome',
    'chromedriver',
    'nacl_helper',
  ],
  'win': [
    # No stripping symbols from win64 archives.

  ],
  'mac': [
    # No stripping symbols from Mac archives.
  ],
}
