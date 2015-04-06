# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from common import cros_chromite
from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Dict, Single, Set

from RECIPE_MODULES.path import api as path_api


def BaseConfig(**_kwargs):
  return ConfigGroup(
    # Base mapping of repository key to repository name.
    repositories = Dict(value_type=Set(basestring)),

    # Checkout Chromite at this revision.
    chromite_revision = Single(basestring),

    cbb = ConfigGroup(
      # The buildroot directory name to use.
      builddir = Single(basestring),

      # If supplied, forward to cbuildbot as '--master-build-id'.
      build_id = Single(basestring),

      # If supplied, forward to cbuildbot as '--chrome-rev'.
      chrome_rev = Single(basestring),

      # If supplied, forward to cbuildbot as '--chrome_version'.
      chrome_version = Single(basestring),

      # If True, add cbuildbot flag: '--debug'.
      debug = Single(bool),

      # If True, add cbuildbot flag: '--clobber'.
      clobber = Single(bool),
    ),
  )

config_ctx = config_item_context(BaseConfig, {}, 'basic')


@config_ctx()
def base(c):
  c.repositories['tryjob'] = []
  c.repositories['chromium'] = []
  c.repositories['cros_manifest'] = []
  c.chromite_revision = 'master'


@config_ctx(includes=['base'])
def external(c):
  c.repositories['tryjob'].append(
      'https://chromium.googlesource.com/chromiumos/tryjobs')
  c.repositories['chromium'].append(
      'https://chromium.googlesource.com/chromium/src')
  c.repositories['cros_manifest'].append(
      'https://chromium.googlesource.com/chromiumos/manifest-versions')


@config_ctx(group='master', includes=['external'])
def master_chromiumos_chromium(c):
  c.cbb.builddir = 'shared_external'


@config_ctx(group='master', includes=['external'])
def master_chromiumos(c):
  c.cbb.builddir = 'external_master'


@config_ctx()
def chromeos_tryserver_etc(c):
  c.cbb.clobber = True


@config_ctx()
def test_variant(c):
  c.cbb.chrome_rev = 'stable'
  c.cbb.clobber = True
