# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test v8/node.js integration."""

from recipe_engine.recipe_api import Property
from recipe_engine.post_process import Filter, ResultReasonRE, StatusFailure

from PB.go.chromium.org.luci.buildbucket.proto import rpc as rpc_pb2
from PB.google.rpc import code as rpc_code_pb2


DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/commit_position',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'v8',
  'zip',
]

PROPERTIES = {
  # List of tester names to trigger.
  'triggers': Property(default=None, kind=list),
  # Use V8 ToT (HEAD) revision instead of pinned.
  'v8_tot': Property(default=False, kind=bool),
}

ARCHIVE_PATH = 'chromium-v8/node-%s-rel'
ARCHIVE_LINK = 'https://storage.googleapis.com/%s/%%s' % ARCHIVE_PATH


def run_with_retry(api, step_name, step_fun):
  """Runs `step_fun` and retries once on failure.

  Returns: True if a flake has been detected.
  """
  # First try. Be forgiving and bail out if it passes.
  try:
    step_fun(step_name=step_name)
    return False
  except api.step.StepFailure:
    api.step.active_result.presentation.status = api.step.SUCCESS

  # Second try. Let it raise if it fails again.
  step_fun(step_name=step_name + ' (retry)')

  # If the retry didn't raise, we found a flake. We report it in a separate
  # step that's ignored by gatekeeper.
  step_result = api.step(step_name + ' (flakes)', cmd=None)
  step_result.presentation.status = api.step.FAILURE
  return True


def RunSteps(api, triggers, v8_tot):
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

  # Archive node executable and trigger performance bots on V8 ToT builders.
  if v8_tot:
    revision = api.bot_update.last_returned_properties['got_revision']
    revision_cp = api.bot_update.last_returned_properties['got_revision_cp']
    _, revision_number = api.commit_position.parse(revision_cp)
    revision_number = str(revision_number)

    with api.step.nest('archive') as parent:
      archive_name = ('node-%s-rel-%s-%s.zip' %
                      (api.platform.name, revision_number, revision))
      zip_file = api.path['cleanup'].join(archive_name)

      # Zip build.
      package = api.zip.make_package(build_output_path, zip_file)
      package.add_file(
          build_output_path.join('node'), api.path.join('bin', 'node'))
      package.zip('zipping')

      # Upload to google storage bucket.
      api.gsutil.upload(
        zip_file,
        ARCHIVE_PATH % api.platform.name,
        archive_name,
        args=['-a', 'public-read'],
      )

      parent.presentation.links['download'] = (
          ARCHIVE_LINK % (api.platform.name, archive_name))

    if triggers:
      api.v8.buildbucket_trigger(
          [(builder_name, {
            'revision': revision,
            'parent_got_revision': revision,
            'parent_got_revision_cp': revision_cp,
            'parent_buildername': api.buildbucket.builder_name,
          }) for builder_name in triggers],
          project='v8-internal',
          bucket='ci')

  # Run tests.
  has_flakes = False
  with api.context(cwd=api.path['checkout'].join('node')):
    run_cctest = lambda step_name: api.step(
        step_name, [build_output_path.join('node_cctest')])
    has_flakes |= run_with_retry(api, 'run cctest', run_cctest)

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
        '--shell', build_output_path.join('node'),
      ]
      if use_test_root:
        args += ['--test-root', build_output_path.join('gen', 'node', 'test')]
      run_test = lambda step_name: api.python(
          name=step_name,
          script=api.path.join('tools', 'test.py'),
          args=args + [suite],
      )
      has_flakes |= run_with_retry(api, 'test ' + suite, run_test)

  # Make flakes visible on the waterfall. This is not tracked by gatekeeper.
  if has_flakes:
    raise api.step.StepFailure('Flakes in build')


def _sanitize_nonalpha(*chunks):
  return '_'.join(
      ''.join(c if c.isalnum() else '_' for c in text)
      for text in chunks
  )


def GenTests(api):
  def test(buildername, platform, is_trybot=False, suffix='', **properties):
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
        api.test(_sanitize_nonalpha('full', buildername) + suffix) +
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
  ) + api.post_process(Filter('initialization.bot_update'))

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
      triggers=['v8_foobar_perf'],
      v8_tot=True,
  )

  # Test CI builder on V8 master.
  yield (
      test(
          'V8 Foobar',
          platform='linux',
          suffix='_trigger_fail',
          triggers=['v8_foobar_perf'],
          v8_tot=True,
      ) + api.buildbucket.simulated_schedule_output(
          rpc_pb2.BatchResponse(
              responses=[dict(error=dict(
                  code=rpc_code_pb2.PERMISSION_DENIED,
                  message='foobar',
              ))],
          ),
          step_name='trigger',
      ) +
      api.post_process(Filter('trigger', '$result'))
  )

  # Test CI builder on V8 master with consistent test failures.
  yield (
      test(
          'V8 Foobar',
          platform='linux',
          suffix='_test_failure',
          triggers=['v8_foobar_perf'],
          v8_tot=True,
      ) +
      api.step_data('test default', retcode=1) +
      api.step_data('test default (retry)', retcode=1) +
      api.post_process(StatusFailure) +
      api.post_process(Filter('test default', 'test default (retry)'))
  )

  # Test CI builder on V8 master with flakes.
  yield (
      test(
          'V8 Foobar',
          platform='linux',
          suffix='_flake',
          triggers=['v8_foobar_perf'],
          v8_tot=True,
      ) +
      api.step_data('test default', retcode=1) +
      api.post_process(StatusFailure) +
      api.post_process(ResultReasonRE, 'Flakes in build') +
      api.post_process(Filter(
          'test default', 'test default (retry)', 'test default (flakes)'))
  )
