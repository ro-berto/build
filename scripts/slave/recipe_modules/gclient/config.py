# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from slave.recipe_configs_util import config_item_context, ConfigGroup, BadConf
from slave.recipe_configs_util import DictConfig, SimpleConfig, StaticConfig
from slave.recipe_configs_util import SetConfig, ConfigList, ListConfig

def BaseConfig(USE_MIRROR=True, GIT_MODE=False, CACHE_DIR=None, **_kwargs):
  deps = '.DEPS.git' if GIT_MODE else 'DEPS'
  cache_dir = str(CACHE_DIR) if GIT_MODE and CACHE_DIR else None
  return ConfigGroup(
    solutions = ConfigList(
      lambda: ConfigGroup(
        name = SimpleConfig(str),
        url = SimpleConfig(str),
        deps_file = SimpleConfig(str, empty_val=deps, required=False),
        managed = SimpleConfig(bool, empty_val=True, required=False),
        custom_deps = DictConfig(value_type=(str, types.NoneType)),
        custom_vars = DictConfig(value_type=str),
        safesync_url = SimpleConfig(str, required=False),

        revision = SimpleConfig(str, required=False, hidden=True),
      )
    ),
    deps_os = DictConfig(value_type=str),
    hooks = ListConfig(str),
    target_os = SetConfig(str),
    target_os_only = SimpleConfig(bool, empty_val=False, required=False),
    cache_dir = StaticConfig(cache_dir, hidden=False),

    GIT_MODE = StaticConfig(bool(GIT_MODE)),
    USE_MIRROR = StaticConfig(bool(USE_MIRROR)),
  )

VAR_TEST_MAP = {
  'USE_MIRROR': (True, False),
  'GIT_MODE':   (True, False),
  'CACHE_DIR':  (None, 'CACHE_DIR'),
}

TEST_NAME_FORMAT = lambda kwargs: (
  'using_mirror-%(USE_MIRROR)s-git_mode-%(GIT_MODE)s-cache_dir-%(using)s' %
  dict(using=bool(kwargs['CACHE_DIR']), **kwargs)
)

config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_NAME_FORMAT)

def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)

def ChromiumGitURL(_c, *pieces):
  return '/'.join(('https://chromium.googlesource.com',) + pieces)

def ChromiumSrcURL(c):
  if c.GIT_MODE:
    return ChromiumGitURL(c, 'chromium', 'src.git')
  else:
    return ChromiumSvnSubURL(c, 'chrome', 'trunk', 'src')

def BlinkURL(c):
  if c.GIT_MODE:
    return ChromiumGitURL(c, 'chromium', 'blink.git')
  else:
    return ChromiumSvnSubURL(c, 'blink', 'trunk')

def mirror_only(c, obj):
  return obj if c.USE_MIRROR else obj.__class__()

@config_ctx()
def chromium_bare(c):
  s = c.solutions.add()
  s.name = 'src'
  s.url = ChromiumSrcURL(c)
  s.custom_vars = mirror_only(c, {
    'googlecode_url': 'svn://svn-mirror.golo.chromium.org/%s',
    'nacl_trunk': 'svn://svn-mirror.golo.chromium.org/native_client/trunk',
    'sourceforge_url': 'svn://svn-mirror.golo.chromium.org/%(repo)s',
    'webkit_trunk': 'svn://svn-mirror.golo.chromium.org/blink/trunk'})

@config_ctx(includes=['chromium_bare'])
def chromium_empty(c):
  c.solutions[0].deps_file = ''

@config_ctx(includes=['chromium_bare'])
def chromium(c):
  s = c.solutions[0]
  s.custom_deps = mirror_only(c, {
    'src/third_party/WebKit/LayoutTests': None,
    'src/webkit/data/layout_tests/LayoutTests': None})

@config_ctx()
def blink_bare(c):
  s = c.solutions.add()
  s.name = 'blink'
  s.url = BlinkURL(c)

@config_ctx(includes=['chromium'])
def blink(c):
  c.solutions[0].custom_deps = {
    'src/third_party/WebKit': BlinkURL(c)
  }
  c.solutions[0].custom_vars['webkit_revision'] = 'HEAD'

@config_ctx()
def nacl(c):
  if c.GIT_MODE:
    raise BadConf('nacl only supports svn')
  s = c.solutions.add()
  s.name = 'native_client'
  s.url = ChromiumSvnSubURL(c, 'native_client', 'trunk', 'src', 'native_client')
  s.custom_vars = mirror_only(c, {
    'webkit_trunk': 'svn://svn-mirror.golo.chromium.org/blink/trunk',
    'googlecode_url': 'svn://svn-mirror.golo.chromium.org/%s',
    'sourceforge_url': 'svn://svn-mirror.golo.chromium.org/%(repo)s'})

  s = c.solutions.add()
  s.name = 'supplement.DEPS'
  s.url = ChromiumSvnSubURL(c, 'native_client', 'trunk', 'deps',
                            'supplement.DEPS')

@config_ctx()
def tools_build(c):
  if not c.GIT_MODE:
    raise BadConf('tools_build only supports git')
  s = c.solutions.add()
  s.name = 'build'
  s.url = ChromiumGitURL(c, 'chromium', 'tools', 'build.git')


