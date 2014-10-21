# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
]


def _CheckoutSteps(api):
  # Checkout mojo and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('mojo')
  api.gclient.checkout()
  api.gclient.runhooks()


def _BuildSteps(api):
  gn_path = api.path['depot_tools'].join('gn.py')
  api.step('gn', [gn_path, "gen", "out/Debug"], cwd=api.path['checkout'])

  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.sh')
  api.step('mojob build', [mojob_path, '--debug', 'build'])

def _RunTests(api):
  mojob_path = api.path['checkout'].join('mojo', 'tools', 'mojob.sh')
  api.step('mojob test', [mojob_path, '--debug', 'test'])

def GenSteps(api):
  _CheckoutSteps(api)
  _BuildSteps(api)
  _RunTests(api)

def GenTests(api):
  yield api.test("mojo")
