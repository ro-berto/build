# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
  'trigger'
]


def RunSteps(api):
  buildername = api.properties.get('buildername')
  (buildername, _, channel) = buildername.rpartition('-')
  assert channel in ['be', 'dev', 'stable']

  api.python.inline('wait 15 minutes', 'import time; time.sleep(900)')

  postfix = '-' + channel
  buildernames = [
    'dart2js-linux-drt-1-2' + postfix,
    'dart2js-linux-drt-2-2' + postfix,
    'dart2js-linux-drt-csp-minified' + postfix,
    'dart2js-win8-ie10' + postfix,
    'dart2js-win8-ie11' + postfix,
    'dart2js-mac10.11-safari-1-3' + postfix,
    'dart2js-mac10.11-safari-2-3' + postfix,
    'dart2js-mac10.11-safari-3-3' + postfix,
    'dart2js-mac10.11-chrome' + postfix,
    'pkg-mac10.11-release' + postfix,
    'pkg-win7-release' + postfix,
    'pkg-linux-release' + postfix,
    'analyzer-mac10.11-release' + postfix,
    'analyzer-win7-release' + postfix,
    'analyzer-linux-release' + postfix,
    'analyzer-win7-release-strong' + postfix,
    'analyzer-mac10.11-release-strong' + postfix,
    'analyzer-linux-release-strong' + postfix,
  ]

  for option in ['minified', 'hostchecked']:
    for shard in range(1,6):
      buildernames.append(
        'dart2js-linux-d8-%s-%s-5' % (option, shard) + postfix)

  for shard in range(1,5):
    buildernames.append('dart2js-linux-jsshell-%s-4' % shard + postfix)
    buildernames.append('dart2js-linux-chromeff-%s-4' % shard + postfix)
    for browser in ['win7-ie10chrome', 'win7-ie11ff']:
      buildernames.append('dart2js-%s-%s-4' % (browser, shard) + postfix)

  triggers = [{'builder_name': name} for name in buildernames]
  api.trigger(*triggers)


def GenTests(api):
  yield (
    api.test('sdk-trigger-be') +
    api.properties.generic(mastername='client.dart',
                           buildername='sdk-trigger-be',
                           revision='abcd1234efef5656'))
