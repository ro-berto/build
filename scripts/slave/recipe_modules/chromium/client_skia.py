# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_linux
import copy

# The Skia config just clones some regular Chromium builders, except that they
# use an up-to-date Skia.
_builders = ['Linux Builder', 'Linux Tests']
SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-skia-gm',
  },
  'builders': {},
}

for builder_name in _builders:
  builder_cfg = copy.deepcopy(chromium_linux.SPEC['builders'][builder_name])
  builder_cfg['recipe_config'] = 'chromium_skia'
  builder_cfg['testing']['test_spec_file'] = 'chromium.linux.json'
  SPEC['builders'][builder_name] = builder_cfg
