# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'trigger',
]

def BuildBuilderNames(name, channel, shards=None):
  if not shards:
    return ['%s-%s' % (name, channel)]
  return ['%s-%s-%s-%s' % (name, i, shards, channel)
          for i in range(1, shards + 1)]

def RunSteps(api):
  (buildername, _, channel) = api.properties.get('buildername').rpartition('-')
  assert channel in ['be', 'dev', 'stable']

  (_, _, os) = buildername.rpartition('-')
  assert os in ['linux', 'windows', 'mac']

  # Step 1) Get the SDK checkout.
  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')


  with api.step.context({'cwd': api.path['checkout']}):
    # Step 2) Run taskkill.
    with api.step.defer_results():
      api.python('taskkill before',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=[],
                 ok_ret='any')

    # Step 3) We always do clean builds on the sdk builders.
    api.python('clobber',
               api.path['tools'].join('clean_output_directory.py'))

    # Step 4) Run the old annotated steps.
    # TODO(kustermann/whesse): We might consider pulling some of the steps
    # of 'tools/bots/dart_sdk.py' out to here.
    api.python('generate sdks',
        api.path['checkout'].join('tools', 'bots', 'dart_sdk.py'),
        args=[])

    # Step 5) Run taskkill.
    api.python('taskkill after',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=[],
               ok_ret='any')

  # Step 6) Trigger dependent builders.
  buildernames = {
    'linux' : (
        BuildBuilderNames('analyzer-linux-release', channel) +
        BuildBuilderNames('analyzer-linux-release-strong', channel) +
        BuildBuilderNames('dart2js-linux-chromeff', channel, 4) +
        BuildBuilderNames('dart2js-linux-d8-hostchecked', channel, 5) +
        BuildBuilderNames('dart2js-linux-d8-minified', channel, 5) +
        BuildBuilderNames('dart2js-linux-drt', channel, 2) +
        BuildBuilderNames('dart2js-linux-drt-csp-minified', channel) +
        BuildBuilderNames('dart2js-linux-jsshell', channel, 4) +
        BuildBuilderNames('pkg-linux-release', channel)
    ),
    'windows' : (
        BuildBuilderNames('analyzer-win7-release', channel) +
        BuildBuilderNames('analyzer-win7-release-strong', channel) +
        BuildBuilderNames('dart2js-win7-ie10chrome', channel, 4) +
        BuildBuilderNames('dart2js-win7-ie11ff', channel, 4) +
        BuildBuilderNames('dart2js-win8-ie10', channel) +
        BuildBuilderNames('dart2js-win8-ie11', channel) +
        BuildBuilderNames('pkg-win7-release', channel)
    ),
    'mac' : (
        BuildBuilderNames('analyzer-mac10.11-release', channel) +
        BuildBuilderNames('analyzer-mac10.11-release-strong', channel) +
        BuildBuilderNames('dart2js-mac10.11-chrome', channel) +
        BuildBuilderNames('dart2js-mac10.11-safari', channel, 3) +
        BuildBuilderNames('pkg-mac10.11-release', channel)
    ),
  }[os]

  triggers = [{'builder_name': name} for name in buildernames]
  api.trigger(*triggers)


def GenTests(api):
  yield (
    api.test('dart-sdk-linux-be') +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-linux-be',
                           revision='abcd1234efef5656'))
  yield (
    api.test('dart-sdk-windows-dev') +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-windows-dev',
                           revision='abcd1234efef5656'))
  yield (
    api.test('dart-sdk-mac-stable') +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-mac-stable',
                           revision='abcd1234efef5656'))
