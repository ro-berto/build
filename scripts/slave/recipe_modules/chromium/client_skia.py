# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_linux
from . import chromium_mac
from . import chromium_win
from common.skia import builder_name_schema
import copy

# The Skia config just clones some regular Chromium builders, except that they
# use an up-to-date Skia.

# This list specifies which Chromium builders to "copy".
_builders = [
#  SPEC Module     Test Spec File         Builder Names
  (chromium_linux, 'chromium.linux.json', ['Linux Builder', 'Linux Tests']),
  (chromium_win,   'chromium.win.json',   ['Win Builder', 'Win7 Tests (1)']),
  (chromium_mac,   'chromium.mac.json',   ['Mac Builder', 'Mac10.9 Tests']),
]

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-skia-gm',
  },
  'builders': {},
}

for spec_module, test_spec_file, builders_list in _builders:
  for builder in builders_list:
    for builder_name in (builder, builder_name_schema.TrybotName(builder)):
      builder_cfg = copy.deepcopy(spec_module.SPEC['builders'][builder])
      builder_cfg['recipe_config'] = 'chromium_skia'
      builder_cfg['testing']['test_spec_file'] = test_spec_file
      builder_cfg['patch_root'] = 'src/third_party/skia'
      SPEC['builders'][builder_name] = builder_cfg
