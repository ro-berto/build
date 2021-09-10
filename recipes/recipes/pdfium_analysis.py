# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'builder_group',
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/gerrit',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/cipd',
    'recipe_engine/platform',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/tricium',
]


def GetChangedFiles(api, checkout_path):
  files = []
  if api.m.tryserver.gerrit_change:
    patch_root = api.gclient.get_gerrit_patch_root()
    assert patch_root, ('local path is not configured for {}'.format(
        api.m.tryserver.gerrit_change_repo_url))
    with api.context(cwd=checkout_path):
      files = api.m.tryserver.get_files_affected_by_patch(patch_root)
    for i, path in enumerate(files):
      path = str(path)
      files[i] = api.path.relpath(path, checkout_path)
  return files


def RunSteps(api):
  """This recipe runs quick legacy analyzers for the pdfium repo.

  The purpose of this recipe is to wrap analyzers that were previously
  triggered directly by Tricium for the pdfium/src repo, in order to
  transition to recipe-based analyzers only.
  """
  # All the analyzers run here must run on 64-bit Linux.
  assert api.platform.is_linux and api.platform.bits == 64
  commit_message = api.gerrit.get_change_description(
      'https://%s' % api.m.tryserver.gerrit_change.host,
      api.m.tryserver.gerrit_change.change,
      api.m.tryserver.gerrit_change.patchset)

  api.gclient.set_config('pdfium')
  # We want line numbers for the file as it is in the CL, not as it is
  # rebased on origin/main. BotUpdateApi.ensure_checkout() by default
  # prevents rebasing and ensures the correct line numbers.
  api.bot_update.ensure_checkout()
  input_dir = api.path['checkout']
  affected_files = [
      f for f in GetChangedFiles(api, input_dir)
      if 'third_party/' not in f and api.path.exists(input_dir.join(f))
  ]
  analyzers = [
      api.tricium.analyzers.HTTPS_CHECK,
      api.tricium.analyzers.OBJECTIVE_C_STYLE,
      api.tricium.analyzers.SPELLCHECKER,
  ]
  api.tricium.run_legacy(analyzers, input_dir, affected_files, commit_message)


def GenTests(api):

  def test_with_patch(name, affected_files):
    test = api.test(
        name,
        api.buildbucket.try_build(
            project='pdfium', builder='tricium_pdfium', patch_set=1),
        api.platform('linux', 64),
        api.builder_group.for_current('cleint.pdfium'),
        api.override_step_data(
            'gerrit changes',
            api.json.output([{
                'revisions': {
                    'aaaa': {
                        '_number': 1,
                        'commit': {
                            'message': 'my commit msg',
                        }
                    }
                }
            }])),
    )
    existing_files = [
        api.path['cache'].join('builder', 'pdfium', x) for x in affected_files
    ]
    test += api.path.exists(*existing_files)
    return test

  yield test_with_patch('one_file', ['README.md']) + api.post_check(
      post_process.StatusSuccess) + api.post_process(
          post_process.DropExpectation)
