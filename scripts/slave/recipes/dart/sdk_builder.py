# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'trigger',
]

PROPERTIES = {
  'revision': Property(help="SDK builder must be triggered with a revision"),
  'buildername': Property(help="Should end in -[channel]"),
}

def BuildBuilderNames(name, channel, shards=None):
  if not shards:
    return ['%s-%s' % (name, channel)]
  return ['%s-%s-%s-%s' % (name, i, shards, channel)
          for i in range(1, shards + 1)]

def RunSteps(api, revision, buildername):
  (_, _, channel) = buildername.rpartition('-')
  assert channel in ['be', 'dev', 'stable']

  # Step 1) Get the SDK checkout.
  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')


  with api.context(cwd=api.path['checkout']):
    # Step 2) Run taskkill.
    with api.step.defer_results():
      api.python('taskkill before',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=[],
                 ok_ret='any')

    # Step 3) Run gclient hooks.
    api.gclient.runhooks()

    # Step 4) We always do clean builds on the sdk builders.
    api.python('clobber',
               api.path['tools'].join('clean_output_directory.py'))

    # Step 5) Build and upload the SDK
    api.python('generate sdks',
        api.path['checkout'].join('tools', 'bots', 'dart_sdk.py'),
        args=[])

    # Step 6) Run taskkill.
    api.python('taskkill after',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=[],
               ok_ret='any')

    # Step 7) Trigger dependent builders.
    buildernames = {
      'linux' : (
          BuildBuilderNames('analyze-linux', channel) +
          BuildBuilderNames('analyzer-linux-release', channel) +
          BuildBuilderNames('analyzer-linux-release-strong', channel) +
          BuildBuilderNames('dart2js-linux-chromeff', channel, 4) +
          BuildBuilderNames('dart2js-linux-d8-minified', channel, 5) +
          BuildBuilderNames('dart2js-linux-drt', channel, 2) +
          BuildBuilderNames('dart2js-linux-drt-csp-minified', channel) +
          BuildBuilderNames('dart2js-linux-jsshell', channel, 4) +
          BuildBuilderNames('pkg-linux-release', channel)
      ),
      'win' : (
          BuildBuilderNames('analyzer-win7-release', channel) +
          BuildBuilderNames('analyzer-win7-release-strong', channel) +
          BuildBuilderNames('dart2js-win7-chrome', channel, 4) +
          BuildBuilderNames('dart2js-win7-ie11ff', channel, 4) +
          BuildBuilderNames('dart2js-win8-ie11', channel, 4) +
          BuildBuilderNames('pkg-win7-release', channel)
      ),
      'mac' : (
          BuildBuilderNames('analyzer-mac10.11-release', channel) +
          BuildBuilderNames('analyzer-mac10.11-release-strong', channel) +
          BuildBuilderNames('dart2js-mac10.11-chrome', channel) +
          BuildBuilderNames('dart2js-mac10.11-safari', channel, 3) +
          BuildBuilderNames('pkg-mac10.11-release', channel)
      ),
    }[api.platform.name]

    triggers = [{'builder_name': name,
                 'properties': { 'revision': revision },
                 } for name in buildernames]
    api.trigger(*triggers)

    # Step 8) Create and upload the API docs
    api.python('generate API docs',
        api.path['checkout'].join('tools', 'bots', 'dart_sdk.py'),
        args=['api_docs'])


def GenTests(api):
  yield (
    api.test('dart-sdk-linux-be') + api.platform('linux', 64) +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-linux-be',
                           revision='abcd1234efef5656'))
  yield (
    api.test('dart-sdk-windows-dev') + api.platform('win', 32) +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-windows-dev',
                           revision='abcd1234efef5656'))
  yield (
    api.test('dart-sdk-mac-stable') + api.platform('mac', 64) +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-mac-stable',
                           revision='abcd1234efef5656'))
