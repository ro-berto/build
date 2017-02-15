# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generates BoringSSL documentation and uploads it to Cloud Storage."""


DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/tryserver',
  'depot_tools/gclient',
  'gsutil',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
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
  with api.step.context({'cwd': util}):
    api.python('generate', go_env, ['go', 'run', 'doc.go', '-out', output])
  if not api.tryserver.is_tryserver:
    # Upload docs only if run after commit, not a tryjob.
    api.gsutil(['-m', 'cp', '-a', 'public-read', api.path.join(output, '**'),
                'gs://chromium-boringssl-docs/'])


def GenTests(api):
  yield (
    api.test('boringssl-docs') +
    api.properties.generic(mastername='client.boringssl',
                           buildername='docs',
                           slavename='slavename')
  )

  yield (
    api.test('boringssl-docs-gerrit') +
    api.properties.tryserver(
        gerrit_project='boringssl',
        gerrit_url='https://boringssl-review.googlesource.com',
        mastername='actually-no-master', buildername='docs',
        slavename='swarming-slave')
  )
