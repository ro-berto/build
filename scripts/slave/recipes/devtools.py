# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'chromium_tests',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
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

def RunSteps(api):
  api.gclient.set_config('chromium')
  api.bot_update.ensure_checkout(force=True)

  has_devtools_file = False
  files = api.chromium_tests.get_files_affected_by_patch()
  for f in files:
    if f.startswith('third_party/WebKit/Source/devtools'):
      has_devtools_file = True

  if not has_devtools_file:
    api.step('skip checks', ['echo', 'no devtools file in patch'])
    return

  def get_devtools_path(*sub_paths):
    devtools_sub_path = ('third_party', 'WebKit', 'Source', 'devtools')
    joined_path = devtools_sub_path + sub_paths
    return api.path['checkout'].join(*joined_path)

  devtools_path = get_devtools_path()
  npm_path = get_devtools_path('scripts', 'buildbot', 'npm.py')
  npm_modules_checkout_path = get_devtools_path('npm_modules')
  node_modules_src_path = get_devtools_path(
      'npm_modules', 'devtools', 'node_modules')
  node_modules_dest_path = get_devtools_path('node_modules')

  api.python('install node.js and npm', npm_path, ['--version'])

  # TODO(chenwilliam): instead of checkout here, add it as DEPS
  api.git.checkout(
      url='https://chromium.googlesource.com/deps/third_party/npm_modules',
      # TODO(chenwilliam): pin this ref to a specific commit
      ref='master',
      dir_path=npm_modules_checkout_path)

  # Moving the node_modules folder within the npm_modules git checkout
  # because npm expects a certain directory layout
  # this is a naive approach to ensure we're using the latest npm_modules
  api.shutil.rmtree(node_modules_dest_path)
  api.shutil.copytree(
      'copy npm modules', node_modules_src_path, node_modules_dest_path)

  api.python('run eslint', npm_path, ['run', 'lint'], cwd=devtools_path)

def GenTests(api):
  for mastername, config in MASTERS.iteritems():
    yield (
      api.test(config['testname'] + '_no_devtools_file') +
      api.properties.generic(
          buildername=config['buildername'],
          mastername=mastername,
      )
    )
    yield (
      api.test(config['testname']  + '_with_devtools_file') +
      api.properties.generic(
          buildername=config['buildername'],
          mastername=mastername,
      ) +
      api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
          'third_party/WebKit/Source/devtools/fake.js\n')
      )
    )
