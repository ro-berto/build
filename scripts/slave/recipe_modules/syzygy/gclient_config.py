# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['gclient'].CONFIG_CTX


@CONFIG_CTX()
def syzygy(c):
  # A syzygy configuration for the gclient module.
  c.got_revision_mapping['src'] = 'got_revision'
  c.delete_unversioned_trees = True

  # Configure the checkout of the Syzygy repository.
  s = c.solutions.add()
  s.name = 'src'
  s.url = 'https://chromium.googlesource.com/syzygy.git'
  s.deps_file = 'DEPS'
  s.managed = False

  # Configure the src-internal checkout.
  s = c.solutions.add()
  s.name = 'src-internal'
  s.url = ('https://chrome-internal.googlesource.com/chrome/syzygy/' +
           'internal.DEPS.git')
  s.managed = False

@CONFIG_CTX(includes=['syzygy'])
def syzygy_x64(dummy_c):
  pass

@CONFIG_CTX(includes=['syzygy'])
def syzygy_official(dummy_c):
  pass

@CONFIG_CTX(includes=['syzygy'])
def kasko_official(dummy_c):
  pass
