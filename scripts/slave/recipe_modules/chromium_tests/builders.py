# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

from . import chromium
from . import chromium_android
from . import chromium_android_fyi
from . import chromium_chrome
from . import chromium_chromiumos
from . import chromium_clang
from . import chromium_dawn
from . import chromium_fuzz
from . import chromium_fyi
from . import chromium_goma
from . import chromium_gpu
from . import chromium_gpu_fyi
from . import chromium_linux
from . import chromium_lkgr
from . import chromium_mac
from . import chromium_memory
from . import chromium_perf
from . import chromium_perf_fyi
from . import chromium_swarm
from . import chromium_webkit
from . import chromium_webrtc
from . import chromium_webrtc_fyi
from . import chromium_win
from . import client_openscreen_chromium
from . import client_v8_chromium
from . import client_v8_fyi
from . import tryserver_chromium_android
from . import tryserver_chromium_linux
from . import tryserver_chromium_mac
from . import tryserver_webrtc

BUILDERS = freeze({
  'chromium': chromium.SPEC,
  'chromium.android': chromium_android.SPEC,
  'chromium.android.fyi': chromium_android_fyi.SPEC,
  'chromium.chrome': chromium_chrome.SPEC,
  'chromium.chromiumos': chromium_chromiumos.SPEC,
  'chromium.clang': chromium_clang.SPEC,
  'chromium.dawn': chromium_dawn.SPEC,
  'chromium.fuzz': chromium_fuzz.SPEC,
  'chromium.fyi': chromium_fyi.SPEC,
  'chromium.goma': chromium_goma.SPEC,
  'chromium.gpu': chromium_gpu.SPEC,
  'chromium.gpu.fyi': chromium_gpu_fyi.SPEC,
  'chromium.linux': chromium_linux.SPEC,
  'chromium.lkgr': chromium_lkgr.SPEC,
  'chromium.mac': chromium_mac.SPEC,
  'chromium.memory': chromium_memory.SPEC,
  'chromium.perf': chromium_perf.SPEC,
  'chromium.perf.fyi': chromium_perf_fyi.SPEC,
  'chromium.swarm': chromium_swarm.SPEC,
  'chromium.webkit': chromium_webkit.SPEC,
  'chromium.webrtc': chromium_webrtc.SPEC,
  'chromium.webrtc.fyi': chromium_webrtc_fyi.SPEC,
  'chromium.win': chromium_win.SPEC,
  'client.openscreen.chromium': client_openscreen_chromium.SPEC,
  'client.v8.chromium': client_v8_chromium.SPEC,
  'client.v8.fyi': client_v8_fyi.SPEC,
  'tryserver.chromium.android': tryserver_chromium_android.SPEC,
  'tryserver.chromium.linux': tryserver_chromium_linux.SPEC,
  'tryserver.chromium.mac': tryserver_chromium_mac.SPEC,
  'tryserver.webrtc': tryserver_webrtc.SPEC,

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
})
