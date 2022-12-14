# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_db
from . import chromium_android
from . import chromium_android_fyi
from . import chromium_chromiumos
from . import chromium_clang
from . import chromium_devtools_frontend
from . import chromium_fuzz
from . import chromium_fyi
from . import chromium_goma
from . import chromium_goma_fyi
from . import chromium_linux
from . import chromium_memory
from . import chromium_perf
from . import chromium_perf_fyi
from . import chromium_perf_calibration
from . import chromium_rust
from . import chromium_swarm
from . import chromium_webrtc
from . import chromium_webrtc_fyi
from . import client_devtools_frontend_integration
from . import client_openscreen_chromium
from . import client_v8_chromium
from . import client_v8_fyi
from . import tryserver_chromium_linux
from . import tryserver_devtools_frontend
from . import tryserver_v8
from . import tryserver_webrtc
from . import migration_testing

# Builders for the chromium.reclient.fyi builder group are all defined
# src-side in infra/config/subprojects/reclient/reclient.star

# The configs for the following builder groups are now specified src-side
# in //infra/config/subprojects/chromium/ci/<builder_group>.star
# * chromium
# * chromium.angle
# * chromium.dawn
# * chromium.gpu
# * chromium.gpu.fyi
# * chromium.mac
# * chromium.swangle
# * chromium.win

BUILDERS = builder_db.BuilderDatabase.create({
    'chromium.android':
        chromium_android.SPEC,
    'chromium.android.fyi':
        chromium_android_fyi.SPEC,
    'chromium.chromiumos':
        chromium_chromiumos.SPEC,
    'chromium.clang':
        chromium_clang.SPEC,
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
    'chromium.linux':
        chromium_linux.SPEC,
    'chromium.memory':
        chromium_memory.SPEC,
    'chromium.perf':
        chromium_perf.SPEC,
    'chromium.perf.fyi':
        chromium_perf_fyi.SPEC,
    'chromium.perf.calibration':
        chromium_perf_calibration.SPEC,
    'chromium.rust':
        chromium_rust.SPEC,
    'chromium.staging':
        chromium_swarm.SPEC,
    'chromium.dev':
        chromium_swarm.SPEC,
    'chromium.webrtc':
        chromium_webrtc.SPEC,
    'chromium.webrtc.fyi':
        chromium_webrtc_fyi.SPEC,
    'client.devtools-frontend.integration':
        client_devtools_frontend_integration.SPEC,
    'client.openscreen.chromium':
        client_openscreen_chromium.SPEC,
    'client.v8.chromium':
        client_v8_chromium.SPEC,
    'client.v8.fyi':
        client_v8_fyi.SPEC,
    'tryserver.chromium.linux':
        tryserver_chromium_linux.SPEC,
    'tryserver.devtools-frontend':
        tryserver_devtools_frontend.SPEC,
    'tryserver.v8':
        tryserver_v8.SPEC,
    'tryserver.webrtc':
        tryserver_webrtc.SPEC,

    # For testing the migration scripts
    'migration.testing':
        migration_testing.SPEC,
})
