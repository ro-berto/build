# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.
"""Recipe for building and deploying the www.chromium.org static website."""

from recipe_engine.post_process import DropExpectation
from recipe_engine.recipe_api import Property

from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

from RECIPE_MODULES.depot_tools.gclient import CONFIG_CTX

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'recipe_engine/tricium',
]

PYTHON_VERSION_COMPATIBILITY = "PY3"


def RunSteps(api):
  api.gclient.set_config('chromium_website')
  with api.context(cwd=api.path['cache'].join('builder')):
    api.bot_update.ensure_checkout()
  api.gclient.runhooks()

  with api.context(cwd=api.m.path['checkout']):
    npmw_path = api.m.path['checkout'].join('npmw')
    api.step('build', [npmw_path, 'build'])

    # TODO(crbug.com/1268676): Change this to `'deploy:prod'` when ready.
    # TODO(crbug.com/1267501): Change this to `'deploy:prod <channel-id>`
    # when running as a tryjob.
    out = api.step(
        'deploy', [npmw_path, 'deploy:staging'],
        stdout=api.raw_io.output(add_output_log=True)).stdout
    out = out.decode('utf-8').strip()

    # pylint: disable=line-too-long
    msg = (
        "Deployed site but don't know where.\n"
        "Please [file a bug](https://bugs.chromium.org/p/chromium/issues/entry?template=Chromium.org+bug)\n"
    )
    # pylint: enable=line-too-long
    url = None
    for line in out.splitlines():
      if 'Hosting URL' in line:
        url = line.split()[-1]
        msg = 'Deployed to %s' % url

  if api.m.tryserver.is_tryserver:  # pragma: no cover
    # TODO(crbug.com/1267501): Change to 'FirebaseHosting/Preview' when
    # deploying to a preview site using the <channel-id>, above.
    api.m.tricium.add_comment('FirebaseHosting/Deploy', msg, path='')
    api.m.tricium.write_comments()

  return result_pb2.RawResult(
      status=common_pb.SUCCESS,
      summary_markdown=msg,
  )

def GenTests(api):
  yield api.test(
      'ci',
      api.step_data(
          'deploy',
          stdout=api.raw_io.output('[1mHosting URL:[22m example.com\n')),
      api.post_process(DropExpectation),
  )

@CONFIG_CTX()
def chromium_website(c):
  s = c.solutions.add()
  s.name = 'chromium_website'
  s.url = 'https://chromium.googlesource.com/website.git'
