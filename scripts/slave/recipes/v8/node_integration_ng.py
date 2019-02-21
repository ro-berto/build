# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test v8/node.js integration."""

from recipe_engine.recipe_api import Property
from recipe_engine.post_process import Filter


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

PROPERTIES = {
  # Use V8 ToT (HEAD) revision instead of pinned.
  'v8_tot': Property(default=False, kind=bool),
}


def RunSteps(api, v8_tot):
  with api.step.nest('initialization'):
    # Set up dependent modules.
    api.chromium.set_config('node_ci')
    api.gclient.set_config('node_ci')
    revision = api.buildbucket.gitiles_commit.id or 'HEAD'
    if v8_tot:
      api.gclient.c.revisions['node-ci'] = 'HEAD'
      api.gclient.c.revisions['node-ci/v8'] = revision
      api.gclient.c.got_revision_reverse_mapping['got_revision'] = 'node-ci/v8'
    else:
      api.gclient.c.revisions['node-ci'] = revision

    # Check out.
    with api.context(cwd=api.path['builder_cache']):
      update_step = api.bot_update.ensure_checkout()
      assert update_step.json.output['did_run']

    api.chromium.runhooks()
    api.chromium.ensure_goma()

  with api.step.nest('build'):
    depot_tools_path = api.path['checkout'].join('third_party', 'depot_tools')
    with api.context(env_prefixes={'PATH': [depot_tools_path]}):
      api.chromium.run_gn(use_goma=True)
      api.chromium.compile(use_goma_module=True)

  build_output_path = api.chromium.c.build_dir.join(
      api.chromium.c.build_config_fs)

  with api.context(cwd=api.path['checkout']):
    api.step('run cctest', [build_output_path.join('node_cctest')])

    suites = [
      ('addons', True),
      ('default', False),
      ('js-native-api', True),
      ('node-api', True),
    ]
    for suite, use_test_root in suites:
      args = [
        '-p', 'tap',
        '-j8',
        '--mode=%s' % api.chromium.c.build_config_fs.lower(),
        '--flaky-tests', 'run',
      ]
      if use_test_root:
        args += ['--test-root', build_output_path.join('gen', 'node', 'test')]
      api.python(
        name='test ' + suite,
        script=api.path.join('tools', 'test.py'),
        args=args + [suite],
      )


def _sanitize_nonalpha(*chunks):
  return '_'.join(
      ''.join(c if c.isalnum() else '_' for c in text)
      for text in chunks
  )


def GenTests(api):
  def test(buildername, platform, is_trybot=False, **properties):
    buildbucket_kwargs = {
        'project': 'v8',
        'git_repo': 'https://chromium.googlesource.com/v8/node-ci',
        'builder': buildername,
        'build_number': 571,
        'revision': 'a' * 40,
    }
    if is_trybot:
      properties_fn = api.properties.tryserver
      buildbucket_fn = api.buildbucket.try_build
      buildbucket_kwargs['change_number'] = 456789
      buildbucket_kwargs['patch_set'] = 12
    else:
      properties_fn = api.properties.generic
      buildbucket_fn = api.buildbucket.ci_build
    return (
        api.test(_sanitize_nonalpha('full', buildername)) +
        properties_fn(
            path_config='kitchen',
            **properties
        ) +
        buildbucket_fn(**buildbucket_kwargs) +
        api.platform(platform, 64) +
        api.v8.hide_infra_steps()
    )

  # Test CI builder on node-ci master.
  yield test(
      'Node-CI Foobar',
      platform='linux',
  )

  # Test try builder on node-ci master.
  yield test(
      'node_ci_foobar_rel',
      platform='linux',
      is_trybot=True,
  )

  # Test CI builder on V8 master.
  yield test(
      'V8 Foobar',
      platform='linux',
      v8_tot=True,
  ) + api.post_process(Filter('initialization.bot_update'))
