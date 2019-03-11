# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A generic recipe that runs a given docker container and exits."""

from recipe_engine.recipe_api import Property
from recipe_engine.config import Dict, Single, List


DEPS = [
  'docker',
  'recipe_engine/properties',
]

PROPERTIES=dict(
  server=Property(
    kind=Single(basestring),
    help='GCP docker server to connect to',
    default='gcr.io',
  ),
  project=Property(
    kind=Single(basestring),
    help='Cloud project containing the image',
    default='chromium-container-registry',
  ),
  image=Property(
    kind=Single(basestring),
    help='Image name within the cloud project',
  ),
  cmd_args=Property(
    kind=List(basestring),
    help='Docker command args',
    default=None,
  ),
  env=Property(
    kind=Dict(value_type=basestring),
    help='Dictionary of env for the container',
    default=None,
  ),
)

def RunSteps(api, server, project, image, cmd_args, env):
  api.docker.login(server=server, project=project)
  api.docker.run(image=image, env=env, cmd_args=cmd_args)


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          image='my-image',
          cmd_args=['echo', 'x'],
          env=dict(k='v'),
      )
  )
