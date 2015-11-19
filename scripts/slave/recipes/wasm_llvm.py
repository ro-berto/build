# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'path',
  'properties',
  'python',
]


def RunSteps(api):
  api.gclient.set_config('wasm_llvm')
  api.bot_update.ensure_checkout(force=True)

  api.python('annotated steps',
             api.path['checkout'].join('buildbot', 'build.py'),
             allow_subannotations=True,
             cwd=api.path['checkout'])


def GenTests(api):
  yield(api.test('linux') +
        api.properties.generic(mastername='client.wasm.llvm',
                               buildername='linux'))
