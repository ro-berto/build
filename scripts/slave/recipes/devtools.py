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
  'recipe_engine/shutil',
  'recipe_engine/step',
]

MASTERS = freeze({
  'chromium.fyi': {
    'buildername': 'Chromium DevTools Linux',
    'testname': 'devtools_fyi',
  },
})

AFFECTED_PATHS = (
  'third_party/WebKit/Source/devtools',
)

def should_skip_checks(api):
  if not api.tryserver.is_tryserver:
    return False
  return all(
      not filename.startswith(AFFECTED_PATHS)
      for filename in api.chromium_checkout.get_files_affected_by_patch())

def RunSteps(api):
  api.gclient.set_config('chromium')
  api.bot_update.ensure_checkout(force=True)

  if should_skip_checks(api):
    api.step('skip checks', ['echo', 'no devtools file in patch'])
    return

  def get_devtools_path(*sub_paths):
    devtools_sub_path = ('third_party', 'WebKit', 'Source', 'devtools')
    joined_path = devtools_sub_path + sub_paths
    return api.path['checkout'].join(*joined_path)

  devtools_path = get_devtools_path()
  node_path = get_devtools_path('scripts', 'buildbot', 'node.py')
  npm_modules_checkout_path = get_devtools_path('npm_modules')
  eslint_path = get_devtools_path(
      'npm_modules', 'node_modules', '.bin', 'eslint')

  api.python('install node.js and npm', node_path, ['--version'])

  # TODO(chenwilliam): instead of checkout here, add it as DEPS
  api.git.checkout(
      url='https://chromium.googlesource.com/deps/third_party/npm_modules',
      ref='8451e3a3fae09eaa18ddeed0c069a8e2f0e3541c',
      dir_path=npm_modules_checkout_path)

  eslint_args = [
    eslint_path, '-c', 'front_end/.eslintrc.js',
    '--ignore-path', 'front_end/.eslintignore', 'front_end'
  ]
  api.python('run eslint', node_path, eslint_args, cwd=devtools_path)


def tryserver_properties(api, mastername, config):
  return api.properties.generic(
      buildername=config['buildername'],
      mastername=mastername,
      rietveld='https://rietveld.example.com',
      issue=1,
      patchset=2,
  )

def GenTests(api):
  for mastername, config in MASTERS.iteritems():
    yield (
      api.test(config['testname'] + '_main') +
      api.properties.generic(
          buildername=config['buildername'],
          mastername=mastername,
      )
    )
    yield (
      api.test(config['testname'] + '_tryserver_no_devtools') +
      tryserver_properties(api, mastername, config)
    )
    yield (
      api.test(config['testname']  + '_tryserver_with_devtools') +
      tryserver_properties(api, mastername, config) +
      api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
          'third_party/WebKit/Source/devtools/fake.js\n')
      )
    )
