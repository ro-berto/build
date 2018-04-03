# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot recipe definition for the various Syzygy continuous builders.

To be tested using a command-line like:

  /build/scripts/slave/recipes.py run syzygy/continuous
      revision=0e9f25b1098271be2b096fd1c095d6d907cf86f7
      mastername=master.client.syzygy
      "buildername=Syzygy Debug"
      bot_id=fake_slave
      buildnumber=1

Places resulting output in build/slave/fake_slave.
"""

from recipe_engine.types import freeze

# Recipe module dependencies.
DEPS = [
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'syzygy',
  'trigger',
]


# Valid continuous builders and the Syzygy configurations they load.
BUILDERS = freeze({
  'Syzygy Debug': ('syzygy', {'BUILD_CONFIG': 'Debug'}),
  'Syzygy Debug x64': ('syzygy_x64', {'BUILD_CONFIG': 'Debug'}),
  'Syzygy Release': ('syzygy', {'BUILD_CONFIG': 'Release'}),
  'Syzygy Release x64': ('syzygy_x64', {'BUILD_CONFIG': 'Release'}),
  'Syzygy Official': ('syzygy_official', {}),

  # Trybots.
  'win_dbg_try': ('syzygy', {'BUILD_CONFIG': 'Debug'}),
  'win_rel_try': ('syzygy', {'BUILD_CONFIG': 'Release'}),
  'win_official_try': ('syzygy_official', {}),
  'win_x64_dbg_try': ('syzygy_x64', {'BUILD_CONFIG': 'Debug'}),
  'win_x64_rel_try': ('syzygy_x64', {'BUILD_CONFIG': 'Release'}),
  'win8_rel_try': ('syzygy', {'BUILD_CONFIG': 'Release'}),
})


from recipe_engine.recipe_api import Property

PROPERTIES = {
  'buildername': Property(),
  'blamelist': Property(),
  'revision': Property(),
}


def RunSteps(api, buildername, blamelist, revision):
  """Generates the sequence of steps that will be run by the slave."""
  assert buildername in BUILDERS

  # Configure the build environment.
  s = api.syzygy
  config, kwargs = BUILDERS[buildername]
  s.set_config(config, **kwargs)
  api.chromium.set_config(config, **kwargs)
  api.gclient.set_config(config, **kwargs)
  is_x64_build = 'x64' in buildername

  # Clean up any running processes on the slave.
  s.taskkill()

  # Checkout and compile the project.
  s.checkout()
  s.runhooks()
  s.compile()

  # Load and run the unittests.
  s.clobber_metrics()
  if is_x64_build:
    unittests = ['syzyasan_rtl_unittests']
  else:
    unittests = s.read_unittests_gypi()

  s.run_unittests(unittests)
  s.archive_metrics()

  build_config = api.chromium.c.BUILD_CONFIG
  if (build_config == 'Release' and not buildername.endswith('_try')
      and not is_x64_build):
    s.randomly_reorder_chrome()
    s.benchmark_chrome()

  if s.c.official_build and not buildername.endswith('_try'):
    assert build_config == 'Release'
    s.archive_binaries()
    s.upload_symbols()

    # Sometimes these come as a tuple, sometimes as a list, which messes up the
    # simulation unittests.
    blamelist = list(blamelist) if type(blamelist) is tuple else blamelist

    # Trigger a smoke test build for the same revision.
    props = {'blamelist': blamelist,
             'buildername': 'Syzygy Smoke Test',
             'revision': revision}
    api.trigger(props)


def GenTests(api):
  """Generates an end-to-end successful test for each builder."""
  for buildername in BUILDERS.iterkeys():
    yield api.syzygy.generate_test(api, buildername)
