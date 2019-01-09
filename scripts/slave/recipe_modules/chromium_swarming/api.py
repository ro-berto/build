# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

from recipe_engine import recipe_api


PER_TARGET_SWARMING_DIMS = collections.defaultdict(dict)
PER_TARGET_SWARMING_DIMS.update({
    'android': {
      'cpu': None,
      'gpu': None,
      'os': 'Android',
    },
    'chromeos': {
      'cpu': None,
      'gpu': None,
      'os': 'ChromeOS',
    }
})


MASTER_SWARMING_PRIORITIES = collections.defaultdict(lambda: 25)
MASTER_SWARMING_PRIORITIES.update({
    'chromium.android.fyi': 35,
    'chromium.fyi': 35,  # This should be lower than the CQ.
    'client.v8.chromium': 35,
    'client.v8.fyi': 35,
})


class ChromiumSwarmingApi(recipe_api.RecipeApi):
  def configure_swarming(self, project_name, precommit, mastername=None,
                         default_priority=None):
    """Configures default swarming dimensions and tags.

    Uses the 'chromium' global config to determine target platform defaults,
    make sure something like chromium_tests.configure_build() has been called
    beforehand.

    Args:
      project_name: Lowercase name of the project, e.g. "blink", "chromium".
      precommit: Boolean flag to indicate whether the tests are running before
          the changes are commited.
      mastername: optional name of the mastername to use to configure the
          default priority of swarming tasks.
      default_priority: optional default_priority to use. Will override the
          priority name inherited from the mastername (or the global default).
    """

    # Set platform-specific default dims.
    target_platform = self.m.chromium.c.TARGET_PLATFORM
    swarming_dims = PER_TARGET_SWARMING_DIMS[target_platform]
    for k, v in swarming_dims.iteritems():
      self.m.swarming.set_default_dimension(k, v)

    self.m.swarming.set_default_dimension('pool', 'Chrome')
    self.m.swarming.add_default_tag('project:%s' % project_name)
    self.m.swarming.default_idempotent = True
    self.m.swarming.show_shards_in_collect_step = True

    if precommit:
      self.m.swarming.default_priority = 30
      self.m.swarming.add_default_tag('purpose:pre-commit')
      requester = self.m.properties.get('requester')
      if requester == 'commit-bot@chromium.org':
        self.m.swarming.add_default_tag('purpose:CQ')
        blamelist = self.m.properties.get('blamelist')
        if len(blamelist) == 1:
          requester = blamelist[0]
      else:
        self.m.swarming.add_default_tag('purpose:ManualTS')
      self.m.swarming.default_user = requester

      patch_project = self.m.properties.get('patch_project')
      if patch_project:
        self.m.swarming.add_default_tag('patch_project:%s' % patch_project)
    else:
      self.m.swarming.default_priority = MASTER_SWARMING_PRIORITIES[mastername]
      self.m.swarming.add_default_tag('purpose:post-commit')
      self.m.swarming.add_default_tag('purpose:CI')

    if default_priority is not None:
      # TODO(crbug.com/876570): We should move the Mojo builders to a
      # different "master" and get rid of this code path; we don't really want
      # different builders on the same master to have different priorities,
      # it makes reasoning about builders harder for sheriffs and troopers.
      self.m.swarming.default_priority = default_priority

    if self.m.runtime.is_experimental:
      # The experimental half of LUCI conversions should be lower than
      # everything else.
      self.m.swarming.default_priority = 40
    if self.m.runtime.is_luci:
      self.m.swarming.add_default_tag('purpose:luci')

    # TODO(tikuta): Remove this (crbug.com/894045).
    self.m.swarming.use_go_client = True
