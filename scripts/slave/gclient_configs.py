# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from slave.recipe_configs_util import config_item_context, ConfigGroup
from slave.recipe_configs_util import DictConfig, SimpleConfig, StaticConfig
from slave.recipe_configs_util import SetConfig, ConfigList, ListConfig

def BaseConfig(USE_MIRROR=True):
  return ConfigGroup(
    solutions = ConfigList(
      lambda: ConfigGroup(
        name = SimpleConfig(str),
        url = SimpleConfig(str),
        deps_file = SimpleConfig(str, empty_val='DEPS', required=False),
        managed = SimpleConfig(bool, empty_val=True, required=False),
        custom_deps = DictConfig(value_type=(str, types.NoneType)),
        custom_vars = DictConfig(value_type=str),
        safesync_url = SimpleConfig(str, required=False),
      )
    ),
    deps_os = DictConfig(value_type=str),
    hooks = ListConfig(str),
    target_os = SetConfig(str),
    target_os_only = SimpleConfig(bool, empty_val=False, required=False),
    USE_MIRROR = StaticConfig(bool(USE_MIRROR)),
  )

config_item = config_item_context(
  BaseConfig,
  {'USE_MIRROR': (True, False)},
  'using_mirror-%(USE_MIRROR)s'
)

def ChromiumSvnURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)

def ChromiumGitURL(_c, *pieces):
  return '/'.join(('https://chromium.googlesource.com',) + pieces)

def mirror_only(c, obj):
  return obj if c.USE_MIRROR else obj.__class__()

@config_item()
def chromium_bare(c):
  s = c.solutions.add()
  s.name = 'src'
  s.url = ChromiumSvnURL(c, 'chrome', 'trunk', 'src')

@config_item(includes=['chromium_bare'])
def chromium(c):
  s = c.solutions[0]
  s.custom_deps = mirror_only(c, {
    'src/third_party/WebKit/LayoutTests': None,
    'src/webkit/data/layout_tests/LayoutTests': None})
  s.custom_vars = mirror_only(c, {
    'googlecode_url': 'svn://svn-mirror.golo.chromium.org/%s',
    'nacl_trunk': 'svn://svn-mirror.golo.chromium.org/native_client/trunk',
    'sourceforge_url': 'svn://svn-mirror.golo.chromium.org/%(repo)s',
    'webkit_trunk': 'svn://svn-mirror.golo.chromium.org/blink/trunk'})

@config_item()
def blink_bare(c):
  s = c.solutions.add()
  s.name = 'blink'
  s.url = ChromiumSvnURL(c, 'blink', 'trunk')

@config_item(includes=['chromium'])
def blink(c):
  c.solutions[0].custom_deps['src/third_party/WebKit'] = (
    ChromiumSvnURL(c, 'blink', 'trunk'))

@config_item()
def nacl(c):
  s = c.solutions.add()
  s.name = 'native_client'
  s.url = ChromiumSvnURL(c, 'native_client', 'trunk', 'src', 'native_client')
  s.custom_vars = mirror_only(c, {
    'webkit_trunk': 'svn://svn-mirror.golo.chromium.org/blink/trunk',
    'googlecode_url': 'svn://svn-mirror.golo.chromium.org/%s',
    'sourceforge_url': 'svn://svn-mirror.golo.chromium.org/%(repo)s'})

  s = c.solutions.add()
  s.name = 'supplement.DEPS'
  s.url = ChromiumSvnURL(c, 'native_client', 'trunk', 'deps', 'supplement.DEPS')

@config_item()
def tools_build(c):
  s = c.solutions.add()
  s.name = 'build'
  s.url = ChromiumGitURL('chromium', 'tools', 'build.git')
  s.deps_file = '.DEPS.git'
