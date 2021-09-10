# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from RECIPE_MODULES.build.tricium_clang_tidy import _clang_tidy_path

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_checkout',
    'goma',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/gerrit',
    'depot_tools/tryserver',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/tricium',
    'tricium_clang_tidy',
]


def _should_skip_linting(api):
  revision_info = api.gerrit.get_revision_info(
      'https://%s' % api.tryserver.gerrit_change.host,
      api.tryserver.gerrit_change.change, api.tryserver.gerrit_change.patchset)

  commit_message = revision_info['commit']['message']
  return commit_message.startswith('Revert')


def RunSteps(api):
  assert api.tryserver.is_tryserver

  if _should_skip_linting(api):
    return

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.gclient.apply_config('use_clang_tidy')

    api.chromium.set_config('chromium')
    api.chromium.apply_config('mb')

    # Do not rebase the patch, so that the Tricium analyzer observes the correct
    # line numbers. Otherwise, line numbers would be relative to origin/main,
    # which may be synced to include changes subsequent to the actual patch.
    api.chromium_checkout.ensure_checkout(gerrit_no_rebase_patch_ref=True)

    api.chromium.runhooks(name='runhooks (with patch)')

    src_dir = api.chromium_checkout.checkout_dir.join('src')
    with api.context(cwd=src_dir):
      affected = [
          src_dir.join(f)
          for f in api.chromium_checkout.get_files_affected_by_patch()
      ]

      api.chromium.ensure_goma()
      api.goma.start()

      # `gn gen` can take up to a minute, and the script we call out to
      # already does that for us, so set up a minimal build dir.
      gn_args = api.chromium.mb_lookup(api.chromium.get_builder_id())
      api.file.ensure_directory('ensure out dir', api.chromium.output_dir)
      api.file.write_text('write args.gn',
                          api.chromium.output_dir.join('args.gn'), gn_args)

      api.tricium_clang_tidy.lint_source_files(api.chromium.output_dir,
                                               affected)


def GenTests(api):

  def test_with_patch(name,
                      affected_files,
                      is_revert=False,
                      author='gbiv@google.com'):
    commit_message = 'Revert foo' if is_revert else 'foo'
    commit_message += '\nTriciumTest'
    test = api.test(
        name,
        api.chromium.try_build(
            builder_group='tryserver.chromium.linux',
            builder='linux_chromium_compile_rel_ng',
            build_number=1234,
            patch_set=1),
        api.platform('linux', 64),
        api.override_step_data(
            'gerrit changes',
            api.json.output([{
                'revisions': {
                    'a' * 40: {
                        '_number': 1,
                        'commit': {
                            'author': {
                                'email': author,
                            },
                            'message': commit_message,
                        }
                    }
                }
            }])),
    )

    existing_files = [
        api.path['cache'].join('builder', 'src', x) for x in affected_files
    ]

    existing_files.append(api.path['cache'].join('builder', 'src',
                                                 *_clang_tidy_path))

    test += api.path.exists(*existing_files)

    return test

  yield (test_with_patch(
      'skip_reverted_cl',
      affected_files=['path/to/some/cc/file.cpp'],
      is_revert=True) +
         api.post_process(post_process.DoesNotRun, 'bot_update') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  # Simple test to improve coverage. All other logic is tested in the
  # tricium_clang_tidy recipe module.
  yield (test_with_patch('no_files', affected_files=[]) +
         api.post_process(post_process.DoesNotRun, 'clang-tidy') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))
