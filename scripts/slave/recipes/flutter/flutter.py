# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/path',
  'recipe_engine/step',
  'depot_tools/git',
]

FLUTTER_CLI_PATH = 'bin/flutter'


def UpdatePackages(api):
  update_packages = api.path['checkout'].join('dev', 'update_packages.dart')
  api.step('update packages', ['dart', update_packages])


def PopulateFlutterCache(api):
  checkout = api.path['checkout']
  flutter_package = checkout.join('packages', 'flutter')
  populate_cmd = [checkout.join(FLUTTER_CLI_PATH), 'cache', 'populate']
  api.step('populate flutter cache', populate_cmd, cwd=flutter_package)


def AnalyzeFlutter(api):
  checkout = api.path['checkout']
  analyze_cmd = [
    checkout.join(FLUTTER_CLI_PATH),
    'analyze',
    '--flutter-repo',
    '--no-current-directory',
    '--no-current-package',
    '--congratulate'
  ]
  api.step('flutter analyze', analyze_cmd)


def TestFlutterPackagesAndExamples(api):
  checkout = api.path['checkout']
  flutter_cli = checkout.join(FLUTTER_CLI_PATH)

  def _pub_test(path):
    api.step('test %s' % path, ['pub', 'run', 'test', '-j1'],
      cwd=checkout.join(path))

  def _flutter_test(path):
    api.step('test %s' % path, [flutter_cli, 'test'],
      cwd=checkout.join(path))

  _pub_test('packages/cassowary')
  _flutter_test('packages/flutter')
  _pub_test('packages/flutter_tools')
  _pub_test('packages/flx')
  _pub_test('packages/newton')

  _flutter_test('examples/stocks')


def RunSteps(api):
  api.git.checkout(
      'https://chromium.googlesource.com/external/github.com/flutter/flutter',
      recursive=True)

  checkout = api.path['checkout']

  download_sdk = checkout.join('infra', 'download_dart_sdk.py')
  api.step('download dart sdk', [download_sdk])

  checkout = api.path['checkout']
  dart_bin = checkout.join('infra', 'dart-sdk', 'dart-sdk', 'bin')
  env = { 'PATH': api.path.pathsep.join((str(dart_bin), '%(PATH)s')) }

  # The context adds dart-sdk tools to PATH.
  with api.step.context({'env': env}):
    UpdatePackages(api)
    PopulateFlutterCache(api)
    AnalyzeFlutter(api)
    TestFlutterPackagesAndExamples(api)


def GenTests(api):
  yield api.test('basic')
