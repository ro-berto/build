# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot recipe definition for the various Syzygy coverage builder.

To be tested using a command-line like:

  /build/scripts/slave/recipes.py run syzygy/continuous
      revision=0e9f25b1098271be2b096fd1c095d6d907cf86f7
      mastername=master.client.syzygy
      "buildername=Syzygy Coverage"
      bot_id=fake_slave
      buildnumber=1

Places resulting output in build/slave/fake_slave. In order for the Coverage
builder to run successfully the appropriate gsutil boto credentials must be
placed in build/site_config/.boto. Cloud storage destinations will be prefixed
with 'test/' in order to not pollute the official coverage archives during
testing.
"""

from recipe_engine.types import freeze

# Recipe module dependencies.
DEPS = [
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'syzygy',
]


# Valid continuous builders.
BUILDERS = freeze({
    'Syzygy Coverage': ('syzygy', {'BUILD_CONFIG': 'Coverage'}),
    'win_cov_try': ('syzygy', {'BUILD_CONFIG': 'Coverage'}),
})

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'buildername': Property(),
}


def RunSteps(api, buildername):
  """Generates the sequence of steps that will be run on the coverage bot."""
  assert buildername in BUILDERS
  # Configure the build environment.
  s = api.syzygy
  config, kwargs = BUILDERS[buildername]
  s.set_config(config, **kwargs)
  api.chromium.set_config(config, **kwargs)
  api.gclient.set_config(config, **kwargs)

  # Clean up any running processes on the slave.
  s.taskkill()

  # Checkout and compile the project.
  s.checkout()
  s.runhooks()
  s.compile()

  s.capture_unittest_coverage()

  if not buildername.endswith('_try'):
    s.archive_coverage()


def GenTests(api):
  """Generates an end-to-end successful test for this builder."""
  for buildername in BUILDERS:
    yield api.syzygy.generate_test(api, buildername)
