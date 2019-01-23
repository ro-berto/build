# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter


DEPS = [
  'depot_tools/git',
  'recipe_engine/buildbucket',
  'recipe_engine/cipd',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
]


def RunSteps(api):
  revision = api.buildbucket.gitiles_commit.id or 'HEAD'
  got_revision = api.git.checkout(url='https://dart.googlesource.com/co19',
      ref=revision, set_got_revision=True)
  co19_path = api.path['checkout']
  package_name = 'dart/third_party/co19'
  pkg = api.cipd.PackageDefinition(package_name, co19_path, 'copy')
  pkg.add_dir(co19_path)
  api.cipd.create_from_pkg(pkg, tags={'git_revision':got_revision})


def GenTests(api):
  yield (
    api.test('basic') +
    api.buildbucket.ci_build(
          builder='co19',
          revision='',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'
    )
  )

  yield (
    api.test('basic-with-revision') +
    api.buildbucket.ci_build(
          builder='co19',
          revision='abcdefgh',
          git_repo='https://dart.googlesource.com/sdk',
          project='dart'
    )
  )

