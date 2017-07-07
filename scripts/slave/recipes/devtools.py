# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'chromium_checkout',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/tryserver',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

MASTERS = freeze({
  'chromium.fyi': {
    'buildername': 'Chromium DevTools Linux',
    'testname': 'devtools_fyi',
  },
  'tryserver.chromium.linux': {
    'buildername': 'chromium_devtools',
    'testname': 'devtools_tryserver',
  },
})

AFFECTED_PATHS = (
  'third_party/WebKit/Source/devtools',
  'third_party/WebKit/Source/core/inspector/browser_protocol.json',
  'v8/src/inspector/js_protocol.json',
)

def should_skip_checks(api):
  if not api.tryserver.is_tryserver:
    return False
  return all(
      not filename.startswith(AFFECTED_PATHS)
      for filename in api.chromium_checkout.get_files_affected_by_patch())

def RunSteps(api):
  api.gclient.set_config('chromium')
  api.bot_update.ensure_checkout()

  if should_skip_checks(api):
    result = api.step('skip checks', ['echo', 'No devtools files in patch.'])
    result.presentation.step_text = "No devtools files in patch."
    return

  def get_devtools_path(*sub_paths):
    devtools_sub_path = ('third_party', 'WebKit', 'Source', 'devtools')
    joined_path = devtools_sub_path + sub_paths
    return api.path['checkout'].join(*joined_path)

  compile_frontend_path = get_devtools_path('scripts', 'compile_frontend.py')
  api.python('compile frontend (closure compiler)', compile_frontend_path)

  # TODO(chenwilliam): re-enable npm step after open source approval
  # See crbug.com/655848

def GenTests(api):
  for mastername, config in MASTERS.iteritems():
    if mastername.startswith('tryserver'):
      yield (
        api.test(config['testname'] + '_no_devtools') +
        api.properties.tryserver(
            buildername=config['buildername'],
            mastername=mastername,
        )
      )
      yield (
        api.test(config['testname']  + '_with_devtools') +
        api.properties.tryserver(
            buildername=config['buildername'],
            mastername=mastername,
        ) +
        api.override_step_data(
            'git diff to analyze patch',
            api.raw_io.stream_output(
                'third_party/WebKit/Source/devtools/fake.js\n'),
        )
      )
    else:
      yield (
        api.test(config['testname']) +
        api.properties.generic(
            buildername=config['buildername'],
            mastername=mastername,
        )
      )
