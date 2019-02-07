# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test v8/node.js integration."""

from recipe_engine.types import freeze


DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'v8',
]

BUILDERS = freeze({
  'V8 Linux64 - node.js integration ng': {
    'testing': {
      'platform': 'linux',
    },
  },
  'v8_node_linux64_rel_ng': {
    'testing': {
      'platform': 'linux',
      'is_trybot': True,
    },
  },
})


def RunSteps(api):
  with api.step.nest('initialization'):
    # Set up dependent modules.
    api.chromium.set_config('node_ci')
    api.gclient.set_config('node_ci')
    revision = api.buildbucket.gitiles_commit.id or 'HEAD'
    api.gclient.c.revisions['node-ci'] = 'HEAD'
    api.gclient.c.revisions['node-ci/v8'] = revision

    # Check out.
    with api.context(cwd=api.path['builder_cache']):
      update_step = api.bot_update.ensure_checkout()
      assert update_step.json.output['did_run']

    api.chromium.runhooks()
    api.goma.ensure_goma()


def _sanitize_nonalpha(*chunks):
  return '_'.join(
      ''.join(c if c.isalnum() else '_' for c in text)
      for text in chunks
  )


def GenTests(api):
  for buildername, bot_config in BUILDERS.iteritems():
    buildbucket_kwargs = {
        'project': 'v8',
        'git_repo': 'https://chromium.googlesource.com/v8/node-ci',
        'builder': buildername,
        'build_number': 571,
        'revision': 'a' * 40,
    }
    if bot_config['testing'].get('is_trybot'):
      properties_fn = api.properties.tryserver
      buildbucket_fn = api.buildbucket.try_build
      buildbucket_kwargs['change_number'] = 456789
      buildbucket_kwargs['patch_set'] = 12
    else:
      properties_fn = api.properties.generic
      buildbucket_fn = api.buildbucket.ci_build
    yield (
        api.test(_sanitize_nonalpha('full', buildername)) +
        properties_fn(
            path_config='kitchen',
        ) +
        buildbucket_fn(**buildbucket_kwargs) +
        api.platform(bot_config['testing']['platform'], 64) +
        api.v8.hide_infra_steps()
    )
