# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(crbug.com/869227): Remove.

DEPS = [
    'chromium_swarming',
    'recipe_engine/platform',
]

from recipe_engine import post_process


def RunSteps(api):
  task = api.chromium_swarming.task(name='net_unittests')
  task.request = task.request.with_slice(
      0, task.request[0].with_dimensions(
          os=api.chromium_swarming.prefered_os_dimension(api.platform.name)))
  api.chromium_swarming.trigger_task(task)


def GenTests(api):
  for plat in ('linux', 'mac', 'win'):
    yield api.test(
        plat,
        api.platform(plat, 64),
        api.post_process(post_process.StatusSuccess),
    )
