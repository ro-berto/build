# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'json',
  'presubmit',
  'properties',
  'rietveld',
  'tryserver',
]


def _GenStepsInternal(api):
  root = api.rietveld.calculate_issue_root(extra_patch_project_roots={'v8': []})
  project = api.properties['patch_project'] or api.properties['project']
  requires_auth = 'internal' in project

  # TODO(iannucci): Pass the build repo info directly via properties
  repo_name = api.properties['repo_name']
  force_checkout = api.properties.get('force_checkout', False)

  api.gclient.set_config(repo_name)

  bot_update_step = api.bot_update.ensure_checkout(
      force=force_checkout, patch_project_roots={'v8': []},
      patch_oauth2=requires_auth)
  relative_root = '%s/%s' % (api.gclient.c.solutions[0].name, root)
  relative_root = relative_root.strip('/')
  got_revision_property = api.gclient.c.got_revision_mapping[relative_root]
  upstream = bot_update_step.json.output['properties'].get(
      got_revision_property)
  if (not upstream or
      isinstance(upstream, int) or
      (upstream.isdigit() and len(upstream) < 40)):
    # If got_revision is an svn revision, then use got_revision_git.
    upstream = bot_update_step.json.output['properties'].get(
        '%s_git' % got_revision_property) or ''

  api.presubmit.commit_patch_locally(root)
  api.presubmit(root=root, upstream=upstream,
                trybot_json_output=api.json.output(),
                use_rietveld_credentials=requires_auth)


def GenSteps(api):
  with api.tryserver.set_failure_hash():
    return _GenStepsInternal(api)


def GenTests(api):
  # TODO(machenbach): This uses the same tryserver for all repos, which doesn't
  # reflect reality (cosmetical problem only). It also misses some repos that
  # use the recipe like tools_build.
  for repo_name in ['blink', 'chromium', 'v8', 'nacl', 'naclports', 'gyp',
                    'infra', 'infra_internal']:
    yield (
      api.test(repo_name) +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='chromium_presubmit',
          repo_name=repo_name,
          patch_project=repo_name) +
      api.step_data('presubmit', api.json.output([['chromium_presubmit',
                                                   ['compile']]]))
    )

  yield (
    api.test('fake_svn_master') +
    api.properties.tryserver(
        mastername='experimental.svn',
        buildername='chromium_presubmit',
        repo_name='chromium',
        force_checkout=True) +
    api.step_data('presubmit', api.json.output([['chromium_presubmit',
                                                 ['compile']]]))
  )
