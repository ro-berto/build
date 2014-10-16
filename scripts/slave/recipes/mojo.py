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
  # Generate build files for Ninja
  gn_path = api.path['depot_tools'].join('gn.py')
  api.step('gn', [gn_path, "gen", "out/Debug"], cwd=api.path['checkout'])

  # Build sample file using Ninja
  debug_path = api.path['checkout'].join('out', 'Debug')
  api.step('compile with ninja', ['ninja', '-C', debug_path, 'mojo'])


def GenSteps(api):
  _CheckoutSteps(api)
  _BuildSteps(api)
  # TODO: Run tests.

def GenTests(api):
  yield api.test("mojo")
