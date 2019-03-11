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
    default='gcr.io',
    help='GCP container registry to pull images from',
  ),
  project=Property(
    kind=Single(basestring),
    default='chromium-container-registry',
    help='Cloud project containing the image',
  ),
  image=Property(
    kind=Single(basestring),
    help='Image name within the cloud project',
  ),
  cmd_args=Property(
    kind=List(basestring),
    default=None,
    help='Docker command args',
  ),
  env=Property(
    kind=Dict(value_type=basestring),
    default=None,
    help='Dictionary of env for the container',
  ),
  inherit_luci_context=Property(
    kind=Dict(value_type=bool),
    default=False,
    help='Inherit current LUCI Context (including auth). '
         'CAUTION: removes network isolation between the container and the '
         'docker host. Read more https://docs.docker.com/network/host/'
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
          inherit_luci_context=True,
      )
  )
