# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.config import Single
from recipe_engine.recipe_api import Property
from recipe_engine.types import freeze

DEPS = [
    'chromium_checkout',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/gitiles',
    'depot_tools/gsutil',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/step',
]

BUILDERS = freeze({
    'chromium-lkgr-finder': {
        'project': 'chromium',
        'repo': 'https://chromium.googlesource.com/chromium/src',
        'ref': 'refs/heads/lkgr',
        'lkgr_status_gs_path': 'chromium-v8/chromium-lkgr-status',
    },
    'V8 lkgr finder': {
        'project': 'v8',
        'repo': 'https://chromium.googlesource.com/v8/v8',
        'ref': 'refs/heads/lkgr',
        'lkgr_status_gs_path': 'chromium-v8/lkgr-status',
        'allowed_lag': 4,
    },
})

PROPERTIES = {
    'project':
        Property(
            kind=str,
            default=None,
            help='Project for which LKGR should be calculated.',
        ),
    'repo':
        Property(
            kind=str,
            default=None,
            help='Repo for which LKGR should be updated.'),
    'ref':
        Property(kind=str, default=None, help='LKGR ref to update.'),
    'src_ref':
        Property(
            kind=str,
            default='refs/heads/master',
            help='Source repo ref to fetch from.'),
    'config':
        Property(
            kind=dict,
            default=None,
            help='Config dict to use. See infra.services.lkgr_finder for more.',
        ),
    'lkgr_status_gs_path':
        Property(
            kind=str,
            default=None,
            help=('Google storage path to which LKGR status reports '
                  'will be uploaded.'),
        ),
    'allowed_lag':
        Property(
            kind=Single((int, float)),
            default=None,
            help='Hours before an LKGR is considered out of date.',
        ),
}


def RunSteps(api, project, repo, ref, config, lkgr_status_gs_path, allowed_lag,
             src_ref):
  # TODO(jbudorick): Remove old_botconfig once the three builders above
  # are explicitly setting their desired properties.
  old_botconfig = BUILDERS.get(api.buildbucket.builder_name)
  if old_botconfig:
    project = project or old_botconfig.get('project')
    repo = repo or old_botconfig.get('repo')
    ref = ref or old_botconfig.get('ref')
    lkgr_status_gs_path = (
        lkgr_status_gs_path or old_botconfig.get('lkgr_status_gs_path'))
    allowed_lag = allowed_lag or old_botconfig.get('allowed_lag')

  if not project or not repo or not ref:
    api.python.failing_step(
        'configuration missing',
        'lkgr_finder requires `project`, `repo`, and `ref` ' +
        'properties to be set.')

  api.gclient.set_config('infra')
  api.gclient.c.revisions['infra'] = 'HEAD'

  # Projects can define revision mappings that conflict with infra revision
  # mapping, so we overide them here to only map infra's revision so that it
  # shows up on the buildbot page.
  api.gclient.c.got_revision_mapping = {}
  api.gclient.c.got_revision_reverse_mapping = {'got_revision': 'infra'}

  checkout_dir = api.chromium_checkout.checkout_dir
  with api.context(cwd=checkout_dir):
    api.bot_update.ensure_checkout()
  api.gclient.runhooks()

  current_lkgr = api.gitiles.commit_log(
      repo, ref, step_name='read lkgr from ref')['commit']

  api.file.ensure_directory('mkdirs builder/lw', checkout_dir.join('lw'))
  args = [
      'infra.services.lkgr_finder',
      '--project=%s' % project,
      '--verbose',
      '--read-from-file',
      api.raw_io.input_text(current_lkgr),
      '--write-to-file',
      api.raw_io.output_text(name='lkgr_hash'),
      '--workdir',
      checkout_dir.join('lw'),
  ]
  if not api.runtime.is_experimental:
    args.append('--email-errors')
  if config:
    args.extend([
        '--project-config-file',
        api.raw_io.input_text(repr(config), name='config_pyl'),
    ])
  step_test_data = api.raw_io.test_api.output_text(
      'deadbeef' * 5, name='lkgr_hash')

  if allowed_lag is not None:
    args.append('--allowed-lag=%d' % allowed_lag)

  if lkgr_status_gs_path:
    args += ['--html', api.raw_io.output_text(name='html')]
    step_test_data += api.raw_io.test_api.output_text(
        '<html>lkgr</html>', name='html')

  try:
    with api.context(cwd=checkout_dir.join('infra')):
      api.python(
          'calculate %s lkgr' % project,
          checkout_dir.join('infra', 'run.py'),
          args,
          step_test_data=lambda: step_test_data)
  except api.step.StepFailure as e:
    # Don't fail the build if the LKGR is just stale.
    if e.result.retcode == 2:
      return
    else:
      raise
  finally:
    step_result = api.step.active_result
    html_status = None
    if (hasattr(step_result, 'raw_io') and
        hasattr(step_result.raw_io, 'output_texts') and
        hasattr(step_result.raw_io.output_texts, 'get')):
      html_status = step_result.raw_io.output_texts.get('html')
    if lkgr_status_gs_path and html_status:
      if api.runtime.is_experimental:
        api.step('fake HTML status upload', cmd=None)
      else:
        api.gsutil.upload(
            api.raw_io.input_text(html_status),
            lkgr_status_gs_path,
            '%s-lkgr-status.html' % project,
            args=['-a', 'public-read'],
            metadata={'Content-Type': 'text/html'},
            link_name='%s-lkgr-status.html' % project,
        )

  # We check out regularly, not only on lkgr update, to catch infra failures
  # on check-out early.
  # TODO(machenbach,tandrii): re-use checkout that the lkgr_finder tool has
  # already made inside its own workdir. Furthermore, one can execute git push
  # command even without having full checkout.
  api.git.checkout(
      url=repo,
      dir_path=checkout_dir.join('workdir'),
      submodules=False,
      submodule_update_recursive=False,
      # For some reason, git cache doesn't make this faster crbug.com/860112.
      use_git_cache=True,
      ref=src_ref,
  )

  new_lkgr = step_result.raw_io.output_texts['lkgr_hash']
  if new_lkgr and new_lkgr != current_lkgr:
    with api.context(cwd=checkout_dir.join('workdir')):
      if api.runtime.is_experimental:
        api.step('fake lkgr push', cmd=None)
      else:
        api.git(
            'push', repo, '%s:%s' % (new_lkgr, ref), name='push lkgr to ref')


def GenTests(api):

  def test_props(buildername):
    return (api.buildbucket.generic_build(builder=buildername))

  def test_props_and_data(buildername):
    return (test_props(buildername) + api.step_data(
        'read lkgr from ref',
        api.gitiles.make_commit_test_data('deadbeef1', 'Commit1')))

  for buildername, botconfig in BUILDERS.iteritems():
    yield (api.test(botconfig['project']) + test_props_and_data(buildername))

  yield (api.test('v8_experimental') + test_props_and_data('V8 lkgr finder') +
         api.runtime(is_experimental=True))

  for retcode, suffix in [(0, ''), (1, '_failure'), (2, '_stale')]:
    yield (
        api.test('custom_properties' + suffix) +
        test_props_and_data('custom-lkgr-finder') +
        api.step_data('calculate custom lkgr', retcode=retcode) +
        api.properties(
            project='custom',
            repo='https://custom.googlesource.com/src',
            ref='refs/heads/lkgr',
            lkgr_status_gs_path='custom/lkgr-status') +
        api.post_process(post_process.MustRun, 'calculate custom lkgr') +
        api.post_process(post_process.StatusCodeIn, 1 if retcode == 1 else 0))

  yield (api.test('missing_all_properties') +
         test_props('missing-lkgr-finder') +
         api.post_process(post_process.MustRun, 'configuration missing') +
         api.post_process(post_process.DropExpectation))

  yield (api.test('custom_config') +
         test_props_and_data('custom-configuration') + api.properties(
             project='custom',
             repo='https://custom.googlesource.com/src',
             ref='refs/heads/lkgr',
             src_ref='refs/heads/master',
             config={
                 'project': 'custom',
                 'source_url': 'https://custom.googlesource.com/src',
                 'masters': {
                     'custom.foo': {
                         'builders': ['custom-foo-builder',],
                     },
                 },
             }) +
         api.post_process(post_process.MustRun, 'calculate custom lkgr') +
         api.post_process(post_process.StepCommandContains,
                          'calculate custom lkgr', ['--project-config-file']) +
         api.post_process(post_process.StatusCodeIn, 0) +
         api.post_process(post_process.DropExpectation))
