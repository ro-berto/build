# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

from . import chromium
from . import chromium_android
from . import chromium_android_fyi
from . import chromium_chrome
from . import chromium_chromiumos
from . import chromium_fyi
from . import chromium_goma
from . import chromium_gpu
from . import chromium_gpu_fyi
from . import chromium_linux
from . import chromium_lkgr
from . import chromium_mac
from . import chromium_memory
from . import chromium_memory_full
from . import chromium_perf
from . import chromium_perf_fyi
from . import chromium_webkit
from . import chromium_webrtc
from . import chromium_webrtc_fyi
from . import chromium_win
from . import client_skia
from . import client_v8_fyi
from . import tryserver_chromium_mac
from . import tryserver_chromium_perf

BUILDERS = freeze({
  'chromium': chromium.SPEC,
  'chromium.android': chromium_android.SPEC,
  'chromium.android.fyi': chromium_android_fyi.SPEC,
  'chromium.chrome': chromium_chrome.SPEC,
  'chromium.chromiumos': chromium_chromiumos.SPEC,
  'chromium.fyi': chromium_fyi.SPEC,
  'chromium.goma': chromium_goma.SPEC,
  'chromium.gpu': chromium_gpu.SPEC,
  'chromium.gpu.fyi': chromium_gpu_fyi.SPEC,
  'chromium.linux': chromium_linux.SPEC,
  'chromium.lkgr': chromium_lkgr.SPEC,
  'chromium.mac': chromium_mac.SPEC,
  'chromium.memory': chromium_memory.SPEC,
  'chromium.memory.full': chromium_memory_full.SPEC,
  'chromium.perf': chromium_perf.SPEC,
  'chromium.perf.fyi': chromium_perf_fyi.SPEC,
  'chromium.webkit': chromium_webkit.SPEC,
  'chromium.webrtc': chromium_webrtc.SPEC,
  'chromium.webrtc.fyi': chromium_webrtc_fyi.SPEC,
  'chromium.win': chromium_win.SPEC,
  'client.skia': client_skia.SPEC,
  'client.v8.fyi': client_v8_fyi.SPEC,
  'tryserver.chromium.mac': tryserver_chromium_mac.SPEC,
  'tryserver.chromium.perf': tryserver_chromium_perf.SPEC,

  # Additional build configurations to test against for coverage. This is useful
  # when adding configuration options that will only be exercised in other
  # repositories.
  #
  # Note that this master is not real, and consequently this build configuration
  # will never be used in production.
  'bot_update.always_on': {
    'builders': {
      'coverage_clobber': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'clobber': True,
        'archive_build': True,
        'testing': {
          'platform': 'linux',
        },
        'gs_bucket': 'invalid',
      },
    },
  },

  # TODO(tikuta): Remove this after removing compile.py.
  'not_compile_py': {
    'builders': {
      'Linux x64 (goma module)': {
         'chromium_config': 'chromium',
         'chromium_apply_config': [
           'clobber',
           'isolation_mode_noop',
           'mb',
           'ninja_confirm_noop',
           'no_dump_symbols',
           'no_compile_py',
         ],
         'gclient_config': 'chromium',
         'chromium_config_kwargs': {
           'BUILD_CONFIG': 'Release',
           'TARGET_BITS': 64,
         },
         'archive_build': True,
         'gs_bucket': 'chromium-browser-snapshots',
         'gs_acl': 'public-read',
         'checkout_dir': 'linux_clobber',
         'testing': {
           'platform': 'linux',
         },
      },
    },
  },
})
