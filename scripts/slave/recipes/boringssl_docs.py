# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generates BoringSSL documentation and uploads it to Cloud Storage."""


DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/runtime',
  'recipe_engine/step',
]


def RunSteps(api):
  # Sync and pull in everything.
  api.gclient.set_config('boringssl')
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

  # Set up paths.
  util = api.path['checkout'].join('util')
  go_env = util.join('bot', 'go', 'env.py')
  output = api.path.mkdtemp('boringssl-docs')

  # Generate and upload documentation.
  with api.context(cwd=util):
    api.python('generate', go_env, ['go', 'run', 'doc.go', '-out', output])
  # Upload docs only if run after commit and on not experimental builds.
  # TODO(tandrii, davidben): remove support for buildbot.
  if api.buildbucket.builder_id.bucket == 'ci' or not api.runtime.is_luci:
    if api.runtime.is_experimental:
      api.step('skipping uploading docs on experimental build', cmd=None)
    else:
      api.gsutil(['-m', 'cp', '-a', 'public-read', api.path.join(output, '**'),
                  'gs://chromium-boringssl-docs/'])


def GenTests(api):
  yield (
    api.test('docs') +
    api.runtime(is_luci=True, is_experimental=False) +
    api.buildbucket.ci_build(
      project='boringssl', bucket='ci', builder='docs')
  )
  yield (
    api.test('docs-experimental') +
    api.runtime(is_luci=False, is_experimental=True) +
    api.properties.generic(mastername='client.boringssl',
                           buildername='docs')
  )

  yield (
    api.test('docs-try') +
    api.runtime(is_luci=True, is_experimental=False) +
    api.buildbucket.try_build(
      project='boringssl', bucket='try', builder='docs',
      gerrit_host='boringssl-review.googlesource.com',
    )
  )
