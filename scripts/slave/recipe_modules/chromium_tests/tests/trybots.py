# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test to ensure the validity of the entries within TRYBOTS.

Each entry in the TRYBOTS dict will be checked to ensure
chromium_tests.trybot_steps can be called with the mastername and buildername
properties set for the entry.
"""

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build.chromium_tests import trybots

DEPS = [
    'chromium',
    'chromium_tests',
    'filter',
    'recipe_engine/properties',
    'recipe_engine/step',
]

def RunSteps(api):
  api.chromium_tests.trybot_steps()
  api.step('Success', ['echo', 'Success!'])

def GenTests(api):
  for builder_id in sorted(trybots.TRYBOTS):
    mastername = builder_id.master
    buildername = builder_id.builder
    yield api.test(
        ('%s-%s' % (mastername, buildername)).replace(' ', '_'),
        (api.properties(xcode_build_version='11c29')
         if 'ios' in buildername else api.properties()),
        api.chromium.try_build(
            mastername=mastername,
            builder=buildername,
        ),
        # Supress analysis so that all targets show up as affected and we run
        # recipe code for each configured test
        api.filter.suppress_analyze(),
        # We want any errors when creating the BotConfig to be surfaced
        # directly to the test rather than creating a failing step
        api.chromium_tests.handle_bot_config_errors(False),
        api.post_process(post_process.DropExpectation),
    )
