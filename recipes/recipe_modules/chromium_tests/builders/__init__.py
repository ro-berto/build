# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_db, bot_spec
from . import chromium
from . import chromium_android
from . import chromium_android_fyi
from . import chromium_angle
from . import chromium_chromiumos
from . import chromium_clang
from . import chromium_dawn
from . import chromium_devtools_frontend
from . import chromium_fuzz
from . import chromium_fyi
from . import chromium_goma
from . import chromium_goma_fyi
from . import chromium_gpu
from . import chromium_gpu_fyi
from . import chromium_linux
from . import chromium_mac
from . import chromium_memory
from . import chromium_mojo
from . import chromium_perf
from . import chromium_perf_fyi
from . import chromium_swangle
from . import chromium_swarm
from . import chromium_updater
from . import chromium_webrtc
from . import chromium_webrtc_fyi
from . import chromium_win
from . import client_devtools_frontend_integration
from . import client_openscreen_chromium
from . import client_v8_chromium
from . import client_v8_fyi
from . import tryserver_chromium_android
from . import tryserver_chromium_linux
from . import tryserver_devtools_frontend
from . import tryserver_webrtc

BUILDERS = bot_db.BotDatabase.create({
    'chromium':
        chromium.SPEC,
    'chromium.android':
        chromium_android.SPEC,
    'chromium.android.fyi':
        chromium_android_fyi.SPEC,
    'chromium.angle':
        chromium_angle.SPEC,
    'chromium.chromiumos':
        chromium_chromiumos.SPEC,
    'chromium.clang':
        chromium_clang.SPEC,
    'chromium.dawn':
        chromium_dawn.SPEC,
    'chromium.devtools-frontend':
        chromium_devtools_frontend.SPEC,
    'chromium.fuzz':
        chromium_fuzz.SPEC,
    'chromium.fyi':
        chromium_fyi.SPEC,
    'chromium.goma.fyi':
        chromium_goma_fyi.SPEC,
    'chromium.goma':
        chromium_goma.SPEC,
    'chromium.gpu':
        chromium_gpu.SPEC,
    'chromium.gpu.fyi':
        chromium_gpu_fyi.SPEC,
    'chromium.linux':
        chromium_linux.SPEC,
    'chromium.mac':
        chromium_mac.SPEC,
    'chromium.memory':
        chromium_memory.SPEC,
    'chromium.mojo':
        chromium_mojo.SPEC,
    'chromium.perf':
        chromium_perf.SPEC,
    'chromium.perf.fyi':
        chromium_perf_fyi.SPEC,
    'chromium.swangle':
        chromium_swangle.SPEC,
    'chromium.staging':
        chromium_swarm.SPEC,
    'chromium.dev':
        chromium_swarm.SPEC,
    'chromium.updater':
        chromium_updater.SPEC,
    'chromium.webrtc':
        chromium_webrtc.SPEC,
    'chromium.webrtc.fyi':
        chromium_webrtc_fyi.SPEC,
    'chromium.win':
        chromium_win.SPEC,
    'client.devtools-frontend.integration':
        client_devtools_frontend_integration.SPEC,
    'client.openscreen.chromium':
        client_openscreen_chromium.SPEC,
    'client.v8.chromium':
        client_v8_chromium.SPEC,
    'client.v8.fyi':
        client_v8_fyi.SPEC,
    'tryserver.chromium.android':
        tryserver_chromium_android.SPEC,
    'tryserver.chromium.linux':
        tryserver_chromium_linux.SPEC,
    'tryserver.devtools-frontend':
        tryserver_devtools_frontend.SPEC,
    'tryserver.webrtc':
        tryserver_webrtc.SPEC,

    # Additional build configurations to test against for coverage.
    # This is useful when adding configuration options
    # that will only be exercised in other repositories.
    #
    # Note that this group is not real, and consequently
    # this build configuration will never be used in production.
    'bot_update.always_on': {
        'coverage_clobber':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                clobber=True,
                archive_build=True,
                simulation_platform='linux',
                gs_bucket='invalid',
            ),
    },
})
