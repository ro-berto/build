# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec
from . import chromium
from . import chromium_chromiumos
from . import chromium_linux
from . import chromium_mac
from . import chromium_win


def chromium_apply_configs(base_config, chromium_config_names,
                           gclient_config_names):
  """chromium_apply_configs returns new config from base config with config.

  It adds chromium_config names in chromium_apply_config.
  It adds gclient_config_names in gclient_apply_config.

  Args:
    base_config: config obj in SPEC[x].
    config_names: a list of config names to be added into chromium_apply_config.
  Returns:
    new config obj.
  """
  return base_config.extend(
      chromium_apply_config=chromium_config_names,
      gclient_apply_config=gclient_config_names,
  )


SPEC = {
    # Staging reclient
    'Linux Builder Re-Client Staging':
        chromium_apply_configs(chromium_linux.SPEC['Linux Builder'], [],
                               ['enable_reclient', 'reclient_staging']),

    # Test reclient
    'Linux Builder Re-Client Test':
        chromium_apply_configs(chromium_linux.SPEC['Linux Builder'], [],
                               ['enable_reclient', 'reclient_test']),
}

# Many of the FYI specs are made by transforming specs from other files, so
# rather than have to do 2 different things for specs based on other specs and
# specs created within this file, just evolve all of the specs afterwards
for name, spec in SPEC.items():
  SPEC[name] = spec.evolve(build_gs_bucket='chromium-fyi-archive')
